import asyncio
from pathlib import Path
from typing import Iterable

from common.exceptions import QbitNotConfiguredException
from components.service_components import BaseServiceComponent
from config import config
from dto.qbit import QBitTorrent
from services.qbit_service import QBitService


class QBitComponent(BaseServiceComponent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._qbit_service = QBitService()

    async def add_torrent(self, torrent_or_magnet_link: str,
                          magnet_hash: str,
                          save_path: str | None,
                          category: str | None = None,
                          tags: list[str] | None = None,
                          resume_on_add: bool = False) -> QBitTorrent | None:
        if not config.user_settings.qbit_base_url:
            raise QbitNotConfiguredException()
        await self._qbit_service.add_torrents(torrent_or_magnet_links=[torrent_or_magnet_link],
                                              save_path=save_path,
                                              category=category,
                                              tags=tags)
        await asyncio.sleep(1)
        if resume_on_add:
            await self._qbit_service.start_torrents(hashes=[magnet_hash])
        return await self.get_torrent(magnet_hash)

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
