from datetime import datetime, UTC, timedelta

from common.db import get_session
from common.decorators import periodic_worker, require_db_session
from components.notification_component import NotificationComponent
from components.operational_components.episode_component import EpisodeComponent
from config import config
from constants import TorrentDownloadStatus, NotificationCode, NotificationLevel, DOWNLOAD_PROCESSING_RETRY_LIMIT
from repositories.notification_repo import NotificationRepo
from repositories.torrent_repositories.torrent_download_repo import TorrentDownloadRepo
from utils.helpers.date_helpers import seconds_to
from workers import BaseWorkerClass


class NotificationWorkers(BaseWorkerClass):

    def __init__(self):
        super().__init__()
        self.notification_component = NotificationComponent()

    @periodic_worker(frequency=30, initial_delay=10)
    @require_db_session
    async def produce_download_error_notifications(self):
        torrent_download_repo = TorrentDownloadRepo(get_session())
        notification_repo = NotificationRepo(get_session())
        torrent_downloads = await torrent_download_repo.get_downloads(
            statuses=[TorrentDownloadStatus.FAILED_DOWNLOAD,
                      TorrentDownloadStatus.FAILED_DOWNLOAD_INIT,
                      TorrentDownloadStatus.FAILED_PROCESSING],
            created_at_after=datetime.now(UTC) - timedelta(hours=72),
            retry_count_minimum=DOWNLOAD_PROCESSING_RETRY_LIMIT,
            load_relations=True
        )
        for torrent_download in torrent_downloads:
            if await notification_repo.get_notification(code=NotificationCode.DOWNLOAD_PROCESSING_PERMANENTLY_FAILED,
                                                        identifier={
                                                            "torrent_download_id": torrent_download.id,
                                                            "status": torrent_download.status.value
                                                        }):
                continue
            action_str = "download" if torrent_download.status == TorrentDownloadStatus.FAILED_DOWNLOAD \
                else "begin downloading" if torrent_download.status == TorrentDownloadStatus.FAILED_DOWNLOAD_INIT \
                else "process"
            text = f"Torrent failed permanently to {action_str}: **{torrent_download.torrent.torrent_title}**"
            await self.notification_component.send_notification(
                code=NotificationCode.DOWNLOAD_PROCESSING_PERMANENTLY_FAILED,
                identifier={
                    "torrent_download_id": torrent_download.id,
                    "status": torrent_download.status.value
                },
                level=NotificationLevel.ERROR,
                text=text
            )

    @periodic_worker(frequency=30, initial_delay=15, listed=False)
    @require_db_session
    async def retract_stale_notifications(self):
        await self.notification_component.evaluate_notifications_staleness()

    @periodic_worker(frequency=60*60*24, initial_delay=seconds_to(hour=21, local=True), listed=False)
    @require_db_session
    async def produce_missing_episodes_report(self):
        if not config.user_settings.notifications_discord_webhook_url \
                or not config.user_settings.discord_send_daily_missing_report:
            return
        await EpisodeComponent().send_tracked_anime_episode_coverage_report()
