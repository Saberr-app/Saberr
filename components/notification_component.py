from datetime import UTC, datetime, timedelta

import aiofiles

from app_state import global_status
from common.db import get_session
from common.decorators import suppress_and_log
from components import BaseComponent
from config import config
from constants import NotificationStatus, NotificationLevel, NotificationCode, TorrentDownloadStatus, SortDirection, \
    AppAsset
from dto.orm_models import Notification
from system import UNSET
from repositories.notification_repo import NotificationRepo
from repositories.torrent_repositories.torrent_download_repo import TorrentDownloadRepo
from services.discord_webhook_service import DiscordWebhookService
from utils.helpers.discord_webhook_helpers import construct_discord_webhook_payload_for_notification


class NotificationComponent(BaseComponent):

    async def send_notification(self,
                                code: NotificationCode,
                                level: NotificationLevel,
                                text: str,
                                identifier: dict | list | None = None,
                                status: NotificationStatus = NotificationStatus.UNREAD,
                                effective_at: datetime = None,
                                send_discord_notification: bool = True):
        if effective_at is None:
            effective_at = datetime.now(UTC)
        notification = await NotificationRepo(get_session()).create_notification(
            code=code,
            level=level,
            text=text,
            identifier=identifier,
            status=status,
            effective_at=effective_at,
        )
        if (config.user_settings.notifications_discord_webhook_url
                and send_discord_notification
                and status == NotificationStatus.UNREAD
                and effective_at <= datetime.now(UTC)):
            await self._send_discord_notification(notification)
        global_status.notifications_updated()

    # noinspection PyMethodMayBeStatic
    async def get_notifications(self,
                                statuses: list[NotificationStatus] | None = None,
                                level: NotificationLevel | None = None,
                                code: NotificationCode | None = None,
                                identifier: dict | list | None = None,
                                effective_before: datetime | None = UNSET,
                                sort_direction: SortDirection = SortDirection.DESC,
                                limit: int | None = 20,
                                offset: int | None = 0) -> list[Notification]:
        if effective_before is UNSET:
            effective_before = datetime.now(UTC)
        return await NotificationRepo(get_session()).get_notifications(
            statuses=statuses,
            level=level,
            code=code,
            identifier=identifier,
            effective_before=effective_before,
            sort_direction=sort_direction,
            limit=limit,
            offset=offset
        )

    # noinspection PyMethodMayBeStatic
    async def get_notification(self, notification_id: int):
        return await NotificationRepo(get_session()).get_notification_by_id(notification_id=notification_id)

    # noinspection PyMethodMayBeStatic
    async def update_notification(self,
                                  notification_id: int,
                                  status: NotificationStatus = None,
                                  effective_at: datetime = None):
        update_data = {}
        if status is not None:
            update_data['status'] = status
        if effective_at is not None:
            update_data['effective_at'] = effective_at
        await NotificationRepo(get_session()).update_notification(
            notification_id=notification_id,
            **update_data
        )
        global_status.notifications_updated()

    # noinspection PyMethodMayBeStatic
    async def mark_unread_notifications_as_read(self):
        await NotificationRepo(get_session()).update_notifications_by_status(
            current_status=NotificationStatus.UNREAD,
            status=NotificationStatus.READ,
        )
        global_status.notifications_updated()

    async def snooze_notification(self, notification_id: int, snooze_duration: timedelta):
        await self.update_notification(notification_id=notification_id,
                                       effective_at=datetime.now(UTC) + snooze_duration)

    async def evaluate_notifications_staleness(self):
        from app_state import downstream_healthcheck_workers
        notifications = await self.get_notifications(statuses=[NotificationStatus.UNREAD],
                                                     effective_before=None,
                                                     limit=None)
        for notification in notifications:
            if not notification.identifier:
                continue
            match notification.code:
                case NotificationCode.DOWNLOAD_PROCESSING_PERMANENTLY_FAILED:
                    torrent_download_id = notification.identifier['torrent_download_id']
                    stuck_status = notification.identifier['status']
                    torrent_download = await TorrentDownloadRepo(get_session()). \
                        get_download(download_id=torrent_download_id)
                    if not torrent_download or torrent_download.status.value != stuck_status:
                        self.logger.debug(f"Marking notification {notification.id} as stale.")
                        await self.update_notification(notification_id=notification.id,
                                                       status=NotificationStatus.STALE)
                case NotificationCode.SERVICE_DOWN:
                    service_code = notification.identifier['service_code']
                    reason = notification.identifier['reason']
                    current_status = downstream_healthcheck_workers.get_status(service_code)
                    if current_status.healthy or current_status.error_details != reason:
                        self.logger.debug(f"Marking notification {notification.id} as stale.")
                        await self.update_notification(notification_id=notification.id,
                                                       status=NotificationStatus.STALE)
                case _:
                    continue

    @suppress_and_log()
    async def _send_discord_notification(self, notification: Notification):
        match notification.code:
            case NotificationCode.DOWNLOAD_PROCESSING_PERMANENTLY_FAILED:
                if not config.user_settings.discord_notify_on_download_failed:
                    self.logger.debug(f"Skipping discord notification for failed download: {notification.id}")
                    return
                torrent_download = await TorrentDownloadRepo(get_session()).get_download(
                    download_id=notification.identifier['torrent_download_id'],
                    load_relations=True
                )
                episode_number = f"#{torrent_download.torrent.tracked_anime_episode.episode_number}"
                if torrent_download.torrent.tracked_anime_episode.tvdb_episode_numbers:
                    episode_number = \
                        (f"Season {torrent_download.torrent.tracked_anime_episode.tvdb_season_number} •"
                         f" Episode {torrent_download.torrent.tracked_anime_episode.tvdb_episode_numbers} "
                         f"({episode_number})")
                fields = [
                    {"name": "Torrent",
                     "value": torrent_download.torrent.torrent_title},
                    {"name": "Anime",
                     "value": torrent_download.torrent.tracked_anime_episode.tracked_anime.preferred_title},
                    {"name": "Episode",
                     "value": episode_number}
                ]
                if torrent_download.destination_path:
                    fields.append({"name": "Destination Path", "value": torrent_download.destination_path})
                match torrent_download.status:
                    case TorrentDownloadStatus.FAILED_DOWNLOAD:
                        title = "Torrent Download Failed"
                        fields.append({"name": "Last error", "value": torrent_download.status_details or "No details"})
                    case TorrentDownloadStatus.FAILED_DOWNLOAD_INIT:
                        title = "Torrent Download Failed to Initialize"
                        fields.append({"name": "Last error", "value": torrent_download.status_details or "No details"})
                    case TorrentDownloadStatus.FAILED_PROCESSING:
                        title = "Torrent Import Failed"
                        fields.append({"name": "Last error", "value": torrent_download.status_details or "No details"})
                    case _:
                        return
            # case NotificationCode.SERVICE_DOWN:
            #     service_status = downstream_healthcheck_workers.get_status(notification.identifier['service_code'])
            #     if service_status.healthy:
            #         return
            #     fields = [
            #         {"name": "Level", "value": service_status.error_level.value},
            #         {"name": "Status code", "value": service_status.error_code or "No code"},
            #         {"name": "Error details", "value": service_status.error_details or "No details"},]
            #     title = f"Downstream Healthcheck Failed - {service_status.name}"
            case NotificationCode.LOGIN:
                if not config.user_settings.discord_notify_on_login:
                    return
                fields = [
                    {"name": key, "value": value} for key, value in
                    {"IP address": notification.identifier['ip_address'],
                     "Country": notification.identifier['country'],
                     "Browser": notification.identifier['browser']}.items()
                ]
                title = "Login"
            case _:
                fields = [
                    {"name": key, "value": value} for key, value in (notification.identifier or {}).items()
                ]
                title = "Notification"
        webhook_payload = construct_discord_webhook_payload_for_notification(notification_id=notification.id,
                                                                             description=notification.text,
                                                                             level=notification.level,
                                                                             fields=fields,
                                                                             title=title,
                                                                             time=notification.effective_at)
        async with aiofiles.open(AppAsset.ICON, 'rb') as icon_file:
            await DiscordWebhookService().send_notification(
                payload=webhook_payload, author_png_image=await icon_file.read()
            )
