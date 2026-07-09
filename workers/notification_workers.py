from datetime import datetime, UTC, timedelta

from common.db import get_session
from common.decorators import periodic_worker, require_db_session
from components.notification_component import NotificationComponent
from constants import TorrentDownloadStatus, NotificationCode, NotificationLevel, DOWNLOAD_PROCESSING_RETRY_LIMIT
from repositories.notification_repo import NotificationRepo
from repositories.torrent_repositories.torrent_download_repo import TorrentDownloadRepo
from workers import BaseWorkerClass


class NotificationWorkers(BaseWorkerClass):

    def __init__(self):
        super().__init__()
        self.notification_component = NotificationComponent()

    @periodic_worker(frequency=30, initial_delay=10)
    @require_db_session
    async def process_notifications(self):
        await self._retract_notifications()
        await self._produce_notifications()

    async def _retract_notifications(self):
        await self.notification_component.evaluate_notifications_staleness()

    async def _produce_notifications(self):
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
