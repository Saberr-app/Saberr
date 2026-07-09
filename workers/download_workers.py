import asyncio
from typing import Coroutine

from common.decorators import periodic_worker, require_db_session
from constants import ExternalServiceCode
from workers import BaseWorkerClass

_DOWNLOADS_LOCK = asyncio.Lock()


class DownloadWorkers(BaseWorkerClass):
    NAME = "Downloads and Processing"

    def __init__(self):
        from components.operational_components.torrent_download_component import TorrentDownloadComponent
        super().__init__()
        self._download_component = TorrentDownloadComponent()

    @periodic_worker(frequency=10, initial_delay=5)
    async def post_download_processing(self):
        from app_state import downstream_healthcheck_workers
        qbit_status = downstream_healthcheck_workers.get_status(ExternalServiceCode.QBIT)
        if not qbit_status.checked or not qbit_status.healthy:
            return
        async with _DOWNLOADS_LOCK:
            await self._advance_downloads_in_pre_downloading_status()
            await self._advance_downloads_in_downloading_status()
            processing_tasks = await self._advance_downloads_in_downloaded_status()
            for processing_task in processing_tasks:
                await processing_task

    @require_db_session
    async def _advance_downloads_in_pre_downloading_status(self):
        await self._download_component.advance_downloads_in_pre_downloading_status()

    @require_db_session
    async def _advance_downloads_in_downloading_status(self):
        await self._download_component.advance_downloads_in_downloading_status()

    @require_db_session
    async def _advance_downloads_in_downloaded_status(self) -> list[Coroutine]:
        return await self._download_component.advance_downloads_in_downloaded_status()

    @periodic_worker(frequency=60, initial_delay=10)
    @require_db_session
    async def stuck_check(self):
        async with _DOWNLOADS_LOCK:
            await self._download_component.mark_stuck_downloads_as_failed()
