import asyncio
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from common.exceptions import QbitNotConfiguredException
from components.service_components import BaseServiceComponent
from config import config
from dto.qbit import QBitTorrent
from services.qbit_service import QBitService
from services.static_files_service import StaticFilesService


class QBitComponent(BaseServiceComponent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._qbit_service = QBitService()
        self._static_files_service = StaticFilesService()

    async def add_torrent(self, torrent_or_magnet_link: str,
                          magnet_hash: str,
                          save_path: str | None,
                          category: str | None = None,
                          tags: list[str] | None = None,
                          resume_on_add: bool = False) -> QBitTorrent | None:
        if not config.user_settings.qbit_base_url:
            raise QbitNotConfiguredException()
        torrent_files = None
        if self._should_proxy_torrent_file(torrent_or_magnet_link):
            torrent_files = [await self._fetch_torrent_file(torrent_or_magnet_link)]
            torrent_or_magnet_link = None
        await self._qbit_service.add_torrents(
            torrent_or_magnet_links=[torrent_or_magnet_link] if torrent_or_magnet_link else [],
            save_path=save_path,
            category=category,
            tags=tags,
            torrent_files=torrent_files)
        await asyncio.sleep(1)
        if resume_on_add:
            await self._qbit_service.start_torrents(hashes=[magnet_hash])
        return await self.get_torrent(magnet_hash)

    @staticmethod
    def _should_proxy_torrent_file(torrent_or_magnet_link: str) -> bool:
        return bool(config.user_settings.rss_proxy_config
                    and config.user_settings.rss_proxy_torrent_files_enabled
                    and torrent_or_magnet_link.lower().startswith(("http://", "https://")))

    async def _fetch_torrent_file(self, torrent_link: str) -> tuple[str, bytes]:
        self.logger.debug(f"Fetching torrent file through proxy: {torrent_link}")
        content = await self._static_files_service.get_arbitrary_file(
            torrent_link, proxy_config=config.user_settings.rss_proxy_config
        )
        file_name = Path(urlparse(torrent_link).path).name or "download"
        if not file_name.endswith(".torrent"):
            file_name = f"{file_name}.torrent"
        return file_name, content

    async def get_torrents(self, magnet_hashes: Iterable[str]) -> list[QBitTorrent]:
        if not magnet_hashes:
            return []
        if not config.user_settings.qbit_base_url:
            raise QbitNotConfiguredException()
        torrents = await self._qbit_service.get_torrents(hashes=magnet_hashes)
        return QBitTorrent.many_from_dict(torrents, remote_path_mapping=config.user_settings.qbit_remote_path_mapping)

    async def get_torrent(self, magnet_hash: str) -> QBitTorrent | None:
        if not config.user_settings.qbit_base_url:
            raise QbitNotConfiguredException()
        torrents = await self._qbit_service.get_torrents(hashes=[magnet_hash])
        if not torrents:
            return None
        return QBitTorrent.from_dict(torrents[0], remote_path_mapping=config.user_settings.qbit_remote_path_mapping)

    async def delete_torrents(self, magnet_hashes: list[str], delete_from_disk: bool = False):
        if not config.user_settings.qbit_base_url:
            raise QbitNotConfiguredException()
        await self._qbit_service.delete_torrents(hashes=magnet_hashes, delete_files=delete_from_disk)

    @staticmethod
    def find_download_files(qbit_torrent: QBitTorrent) -> tuple[Path | None, list[Path]]:
        video_extensions = {'.mkv', '.mp4', '.avi'}
        subtitle_extensions = {'.srt', '.ass', '.ssa', '.sub', '.idx'}
        content_path = Path(qbit_torrent.content_path)

        if content_path.is_file() and content_path.suffix.lower() in video_extensions:
            return content_path, []

        video_file = next(
            (p for p in sorted(content_path.iterdir())
             if p.is_file() and p.suffix.lower() in video_extensions),
            None
        )
        if video_file is None:
            return None, []

        related_files = [
            p for p in sorted(content_path.iterdir())
            if p.is_file() and p != video_file and p.suffix.lower() in subtitle_extensions
            and p.name.startswith(video_file.stem + ".")  # .ass, .en.ass
        ]
        return video_file, related_files
