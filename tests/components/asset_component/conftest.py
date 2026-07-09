from itertools import count
from unittest.mock import AsyncMock

import pytest

from dto.orm_models import CachedAsset


@pytest.fixture(autouse=True)
def fake_cached_asset_store(mocker):
    """In-memory stand-in for CachedAssetRepo so cache-or-fetch flows behave statefully without a DB.
    Keyed by (asset_type, asset_filename) — the unique identity the repo looks assets up by."""
    store: dict[tuple, CachedAsset] = {}
    ids = count(1)

    async def get_cached_asset(*, asset_type, asset_filename=None, remote=None):
        for asset in store.values():
            if asset.asset_type != asset_type:
                continue
            if asset_filename and asset.asset_filename == asset_filename:
                return asset
            if remote and asset.remote == remote:
                return asset
        return None

    async def create_cached_asset(*, asset_filename, asset_type, remote, remote_type, expires_at, deletable):
        asset = CachedAsset(asset_filename=asset_filename, asset_type=asset_type, remote=remote,
                            remote_type=remote_type, expires_at=expires_at, deletable=deletable)
        asset.id = next(ids)
        store[(asset_type, asset_filename)] = asset
        return asset

    async def update_cached_asset_expiration(*, cached_asset_id, new_expiration):
        for asset in store.values():
            if asset.id == cached_asset_id:
                asset.expires_at = new_expiration

    repo = "repositories.cache_repositories.cached_asset_repo.CachedAssetRepo"
    mocker.patch(f"{repo}.get_cached_asset", new=AsyncMock(side_effect=get_cached_asset))
    mocker.patch(f"{repo}.create_cached_asset", new=AsyncMock(side_effect=create_cached_asset))
    mocker.patch(f"{repo}.update_cached_asset_expiration",
                 new=AsyncMock(side_effect=update_cached_asset_expiration))
    return store


@pytest.fixture
def asset_component(tmp_path, monkeypatch):
    """An AssetComponent whose base path (config.data_dir) points at a temp dir (never the real
    data tree), with the network-backed static-files service stubbed out."""
    from config import config
    from components.asset_component import AssetComponent
    monkeypatch.setattr(config, "data_dir", str(tmp_path))
    component = AssetComponent()
    component._static_files_service = AsyncMock()
    return component
