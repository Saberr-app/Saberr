from datetime import datetime, UTC

from sqlalchemy import select, update

from constants import CachedAssetRemoteType, CachedAssetType
from dto.orm_models import CachedAsset
from repositories import BaseRepo


class CachedAssetRepo(BaseRepo):

    # noinspection PyTypeChecker
    async def create_cached_asset(self,
                                  asset_filename: str,
                                  asset_type: CachedAssetType,
                                  remote: str,
                                  remote_type: CachedAssetRemoteType,
                                  expires_at: datetime,
                                  deletable: bool) -> CachedAsset:
        cached_asset = CachedAsset(
            asset_filename=asset_filename,
            asset_type=asset_type,
            remote=remote,
            remote_type=remote_type,
            expires_at=expires_at.astimezone(UTC),
            deletable=deletable
        )
        self._session.add(cached_asset)
        await self._session.flush()
        return cached_asset

    async def get_cached_asset(self,
                               asset_type: CachedAssetType,
                               asset_filename: str | None = None,
                               remote: str | None = None) -> CachedAsset:
        if (not asset_filename and not remote) or (asset_filename and remote):
            raise ValueError("Must specify either asset_filename or remote")
        query = select(CachedAsset).where(CachedAsset.asset_type == asset_type)
        if asset_filename:
            query = query.where(CachedAsset.asset_filename == asset_filename)
        if remote:
            query = query.where(CachedAsset.remote == remote)
        return (await self._session.execute(query)).unique().scalar_one_or_none()

    async def update_cached_asset_expiration(self, cached_asset_id: int,
                                             new_expiration: datetime) -> None:
        await self._session.execute(
            update(CachedAsset).where(CachedAsset.id == cached_asset_id).values(expires_at=new_expiration)
        )
        await self._session.flush()
