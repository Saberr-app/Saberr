from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from constants import CachedAssetRemoteType, CachedAssetType
from dto.orm_models import CachedAsset

_TYPE = CachedAssetType.OTHER


@dataclass
class Case:
    id: str
    seed_existing: bool   # pre-seed a row so persist updates it instead of creating a new one


CASES = [
    Case(id="creates file and row when none exists", seed_existing=False),
    Case(id="updates existing row's expiry rather than creating", seed_existing=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test__persist_asset(case: Case, asset_component, fake_cached_asset_store):
    existing = None
    if case.seed_existing:
        existing = CachedAsset(asset_filename="asset.png", asset_type=_TYPE, remote="http://x/y.png",
                               remote_type=CachedAssetRemoteType.URL,
                               expires_at=datetime.now(UTC) - timedelta(days=5), deletable=True)
        existing.id = 1
        fake_cached_asset_store[(_TYPE, "asset.png")] = existing

    new_expiry = datetime.now(UTC) + timedelta(days=2)
    await asset_component._persist_asset(asset_filename="asset.png", asset_type=_TYPE,
                                         remote="http://x/y.png", remote_type=CachedAssetRemoteType.URL,
                                         data=b"bytes", expires_at=new_expiry, deletable=True,
                                         cached_asset=existing)

    assert asset_component._build_asset_file_path("asset.png", _TYPE).read_bytes() == b"bytes"
    assert (_TYPE, "asset.png") in fake_cached_asset_store
    assert fake_cached_asset_store[(_TYPE, "asset.png")].expires_at == new_expiry
