import base64
import os
import re
from datetime import datetime, UTC, timedelta
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

import aiofiles
import aiofiles.os

from common.exceptions import ExternalImageURLDecodeException
from components import BaseComponent
from config import config
from services.static_files_service import StaticFilesService

_async_utime = aiofiles.os.wrap(os.utime)


class ExternalImageComponent(BaseComponent):
    KNOWN_URL_PREFIXES = {
        "https://s4.anilist.co/file/anilistcdn/media/": "anilist_media",
        "https://s4.anilist.co/file/anilistcdn/character/": "anilist_character",
        "https://s4.anilist.co/file/anilistcdn/staff/": "anilist_staff",
        "https://s4.anilist.co/file/anilistcdn/user/": "anilist_user",
        "https://artworks.thetvdb.com/banners/v4/episode/": "tvdb_episode"
    }
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
    ALLOWED_HOSTS = {r"(.+\.)?anilist\.co", r"(.+\.)?thetvdb\.com"}
    REFETCH_AFTER = timedelta(days=3)
    CLEANUP_AFTER = timedelta(days=14)

    def get_encoded_external_image_url(self, image_url: str) -> str:
        parsed_url = urlparse(image_url)
        if not self._is_allowed_external_image_url(parsed_url):
            return image_url
        return quote(image_url, safe="")

    def get_decoded_external_image_url(self, image_url_encoded: str) -> str:
        if not image_url_encoded:
            raise ExternalImageURLDecodeException()
        decoded_url = unquote(image_url_encoded)
        parsed_url = urlparse(decoded_url)
        if not self._is_allowed_external_image_url(parsed_url):
            raise ExternalImageURLDecodeException()
        return decoded_url

    def _build_image_file_path(self, image_url: str) -> Path:
        subfolder = ""
        encode_target = image_url
        for prefix, folder in self.KNOWN_URL_PREFIXES.items():
            if image_url.startswith(prefix):
                subfolder = folder
                encode_target = image_url[len(prefix):]
                break

        filename_base = base64.urlsafe_b64encode(encode_target.encode()).decode()
        filename_extension = Path(urlparse(image_url).path).suffix
        filename = f"{filename_base}{filename_extension}"

        return Path(config.data_dir) / "images" / subfolder / filename

    def _is_allowed_external_image_url(self, parsed_url) -> bool:
        if parsed_url.scheme not in {"http", "https"}:
            return False
        host = parsed_url.hostname or ""
        if not any(re.fullmatch(pattern, host) for pattern in self.ALLOWED_HOSTS):
            return False
        extension = Path(parsed_url.path).suffix.lower()
        return extension in self.ALLOWED_EXTENSIONS

    async def get_file_path_for_encoded_external_image_url(self, image_url_encoded: str) -> Path:
        image_url = self.get_decoded_external_image_url(image_url_encoded)

        path = self._build_image_file_path(image_url)
        if not path.exists():
            await self._fetch_and_store_external_image(image_url=image_url, save_path=path)
        else:
            last_modified = datetime.fromtimestamp((await aiofiles.os.stat(path)).st_mtime, UTC)
            if datetime.now(UTC) - last_modified > self.REFETCH_AFTER:
                try:
                    await self._fetch_and_store_external_image(image_url=image_url, save_path=path)
                except Exception as e:
                    self.logger.debug(f"Failed to refetch external image {image_url}, serving stale copy: {e}")
        await self._bump_last_activity(path)
        return path

    async def _fetch_and_store_external_image(self, image_url: str, save_path: Path) -> None:
        self.logger.debug(f"Fetching external image {image_url} to {save_path}")
        data = await StaticFilesService().get_arbitrary_file(image_url)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(save_path, "wb") as handle:
            await handle.write(data)

    @staticmethod
    async def _bump_last_activity(path: Path) -> None:
        last_modified = (await aiofiles.os.stat(path)).st_mtime
        await _async_utime(path, (datetime.now(UTC).timestamp(), last_modified))

    async def cleanup_expired_images(self):
        base_dir = Path(config.data_dir) / "images"
        if not base_dir.exists():
            return

        files_on_disk = [path for path in base_dir.rglob("*") if path.is_file()]
        if not files_on_disk:
            return

        expired_by = datetime.now(UTC) - ExternalImageComponent.CLEANUP_AFTER

        removed_files = []
        for path in files_on_disk:
            asset_path = path.as_posix()
            last_accessed = datetime.fromtimestamp((await aiofiles.os.stat(asset_path)).st_atime, UTC)
            if last_accessed < expired_by:
                await aiofiles.os.remove(asset_path)
                removed_files.append(asset_path)

        if removed_files:
            self.logger.info(f"Removed {len(removed_files)} expired external images")
