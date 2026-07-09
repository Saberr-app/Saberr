from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from constants import CachedAssetRemoteType, CachedAssetType
from dto.orm_models import CachedAsset

_TYPE = CachedAssetType.OTHER


@dataclass
class Case:
    id: str
    remote: str
    fresh_bytes: bytes
    expected_result: bytes


CASES = [
    Case(id="url remote refetches, rewrites file and pushes expiry forward",
         remote="http://example.com/a.png", fresh_bytes=b"fresh", expected_result=b"fresh"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test__refresh_cached_asset(case: Case, asset_component, fake_cached_asset_store):
    cached_asset = CachedAsset(asset_filename="asset.png", asset_type=_TYPE, remote=case.remote,
                               remote_type=CachedAssetRemoteType.URL,
                               expires_at=datetime.now(UTC) - timedelta(days=1), deletable=True)
    cached_asset.id = 1
    fake_cached_asset_store[(_TYPE, "asset.png")] = cached_asset
    asset_component._static_files_service.get_arbitrary_file.return_value = case.fresh_bytes

    result = await asset_component._refresh_cached_asset(cached_asset, lifespan=timedelta(days=1))

    assert result == case.expected_result
    assert asset_component._build_asset_file_path("asset.png", _TYPE).read_bytes() == case.expected_result
    asset_component._static_files_service.get_arbitrary_file.assert_awaited_once_with(case.remote)
    # expiry was pushed into the future
    assert fake_cached_asset_store[(_TYPE, "asset.png")].expires_at > datetime.now(UTC)
