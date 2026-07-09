import importlib.util
from datetime import UTC, datetime, timedelta
import hashlib
from pathlib import Path
from urllib.parse import urlparse

import aiofiles
import aiofiles.os

from common.db import get_session
from components import BaseComponent
from config import config
from constants import CachedAssetRemoteType, CachedAssetType
from dto.orm_models import CachedAsset
from repositories.cache_repositories.cached_asset_repo import CachedAssetRepo
from services.static_files_service import StaticFilesService


class AssetComponent(BaseComponent):
    DEFAULT_LIFESPAN = timedelta(days=3)

    def __init__(self):
        super().__init__()
        self._static_files_service = StaticFilesService()

    @property
    def base_path(self) -> str:
        return config.data_dir

    # noinspection PyMethodMayBeStatic
    async def get_cached_asset_object(self, asset_filename: str, asset_type: CachedAssetType) -> CachedAsset | None:
        repo = CachedAssetRepo(get_session())
        return await repo.get_cached_asset(asset_filename=asset_filename, asset_type=asset_type)

    async def get_asset_data(self, url: str, asset_type: CachedAssetType, force_fetch: bool = False,
                             lifespan: timedelta = DEFAULT_LIFESPAN, deletable: bool = True) -> bytes:
        repo = CachedAssetRepo(get_session())
        cached_asset = await repo.get_cached_asset(remote=url, asset_type=asset_type)
        asset_filename = Path(cached_asset.asset_filename) if cached_asset \
            else f"{self._build_asset_filename(url)}"

        if cached_asset and not force_fetch:
            cached_bytes = await self._read_cached_file_if_valid(cached_asset)
            if cached_bytes is not None:
                return cached_bytes

        fetched_bytes = await self._fetch_asset_bytes(url)
        await self._persist_asset(
            asset_filename=asset_filename,
            asset_type=asset_type,
            remote=url,
            remote_type=CachedAssetRemoteType.URL,
            data=fetched_bytes,
            expires_at=datetime.now(UTC) + lifespan,
            deletable=deletable,
            cached_asset=cached_asset
        )
        return fetched_bytes

    async def get_asset_path(self, url: str, asset_type: CachedAssetType, fetch_if_not_exists: bool = False,
                             lifespan: timedelta = DEFAULT_LIFESPAN, deletable: bool = True) -> Path | None:
        repo = CachedAssetRepo(get_session())
        cached_asset = await repo.get_cached_asset(remote=url, asset_type=asset_type)
        if cached_asset:
            if not (path := self._build_asset_file_path(cached_asset.asset_filename,
                                                        cached_asset.asset_type)).exists() and fetch_if_not_exists:
                await self.get_asset_data(url=url, force_fetch=True, lifespan=lifespan,
                                          deletable=deletable, asset_type=asset_type)
            return path
        if not fetch_if_not_exists:
            return None

        asset_path = self._build_asset_file_path(self._build_asset_filename(url), asset_type)
        await self.get_asset_data(url=url, asset_type=asset_type, force_fetch=True, lifespan=lifespan,
                                  deletable=deletable)
        return asset_path

    async def get_asset_data_by_filename(self, asset_filename: str,
                                         asset_type: CachedAssetType,
                                         expired_ok: bool = False,
                                         lifespan: timedelta = DEFAULT_LIFESPAN,
                                         force_fetch: bool = False) -> bytes | None:
        repo = CachedAssetRepo(get_session())
        cached_asset = await repo.get_cached_asset(asset_filename=asset_filename, asset_type=asset_type)
        if not cached_asset:
            return None

        if not force_fetch:
            cached_bytes = await self._read_cached_file_if_valid(cached_asset)
            if cached_bytes is not None:
                return cached_bytes

        try:
            refreshed_bytes = await self._refresh_cached_asset(cached_asset, lifespan=lifespan)
        except Exception as e:
            self.logger.exception(f"Failed to refresh cached asset {asset_type.value} / {asset_filename} "
                                  f" with remote {cached_asset.remote}: {e}")
            if expired_ok:
                return await self._read_cached_file_if_valid(cached_asset, expired_ok=True)
            return None
        return refreshed_bytes

    # noinspection PyMethodMayBeStatic
    def _build_asset_filename(self, url: str) -> str:
        parsed = urlparse(url)
        ext = Path(parsed.path).suffix
        if ext and len(ext) > 10:
            ext = ""
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return f"{digest}{ext}"

    def _build_asset_file_path(self, filename: str, asset_type: CachedAssetType) -> Path:
        base_path = Path(self.base_path) / asset_type.value
        return base_path / filename

    async def _read_cached_file_if_valid(self, cached_asset, expired_ok: bool = False) -> bytes | None:
        if not expired_ok and cached_asset.expires_at <= datetime.now(UTC):
            return None
        file_path = self._build_asset_file_path(cached_asset.asset_filename, cached_asset.asset_type)
        if not file_path.exists():
            self.logger.debug(f"Cached file not found at path {file_path}")
            return None
        async with aiofiles.open(file_path, "rb") as handle:
            return await handle.read()

    async def _fetch_asset_bytes(self, url: str) -> bytes:
        return await self._static_files_service.get_arbitrary_file(url)

    async def _refresh_cached_asset(self, cached_asset, lifespan: timedelta) -> bytes:
        self.logger.debug(f"Refreshing cached asset {cached_asset.asset_type.value} / {cached_asset.asset_filename}")
        if cached_asset.remote_type == CachedAssetRemoteType.URL:
            fetched_bytes = await self._fetch_asset_bytes(cached_asset.remote)
            await self._persist_asset(
                asset_filename=cached_asset.asset_filename,
                asset_type=cached_asset.asset_type,
                remote=cached_asset.remote,
                remote_type=CachedAssetRemoteType.URL,
                data=fetched_bytes,
                expires_at=datetime.now(UTC) + lifespan,
                deletable=cached_asset.deletable,
                cached_asset=cached_asset
            )
        elif cached_asset.remote_type == CachedAssetRemoteType.SCRIPT:
            script_path = Path("scripts/remote") / cached_asset.remote
            if script_path.suffix != ".py":
                script_path = script_path.with_suffix(".py")
            spec = importlib.util.spec_from_file_location(cached_asset.remote, script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            await module.main()
            fetched_bytes = await self._read_cached_file_if_valid(cached_asset,
                                                                  expired_ok=True)  # expired is irrelevant here
            await CachedAssetRepo(get_session()).update_cached_asset_expiration(
                cached_asset_id=cached_asset.id, new_expiration=datetime.now(UTC) + lifespan
            )
        else:
            raise
        return fetched_bytes

    async def _persist_asset(self, asset_filename: str, asset_type: CachedAssetType, remote: str,
                             remote_type: CachedAssetRemoteType, data: bytes, expires_at: datetime, deletable: bool,
                             cached_asset=None) -> None:
        asset_path = self._build_asset_file_path(asset_filename, asset_type)
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(asset_path, "wb") as handle:
            await handle.write(data)

        repo = CachedAssetRepo(get_session())
        if cached_asset:
            await repo.update_cached_asset_expiration(cached_asset_id=cached_asset.id,
                                                      new_expiration=expires_at)
            return
        await repo.create_cached_asset(asset_filename=asset_filename,
                                       asset_type=asset_type,
                                       remote=remote,
                                       remote_type=remote_type,
                                       expires_at=expires_at,
                                       deletable=deletable)
