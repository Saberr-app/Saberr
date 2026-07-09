from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from constants import CachedAssetType

_TYPE = CachedAssetType.OTHER


@dataclass
class Case:
    id: str
    expires_in: timedelta
    file_exists: bool
    expired_ok: bool
    expected_bytes: bytes | None


CASES = [
    Case(id="valid and present returns bytes", expires_in=timedelta(days=1), file_exists=True,
         expired_ok=False, expected_bytes=b"cached"),
    Case(id="expired returns none", expires_in=-timedelta(days=1), file_exists=True,
         expired_ok=False, expected_bytes=None),
    Case(id="expired but expired_ok returns bytes", expires_in=-timedelta(days=1), file_exists=True,
         expired_ok=True, expected_bytes=b"cached"),
    Case(id="missing file returns none", expires_in=timedelta(days=1), file_exists=False,
         expired_ok=False, expected_bytes=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test__read_cached_file_if_valid(case: Case, asset_component):
    file_path = asset_component._build_asset_file_path("asset.bin", _TYPE)
    if case.file_exists:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"cached")
    cached_asset = SimpleNamespace(asset_filename="asset.bin", asset_type=_TYPE,
                                   expires_at=datetime.now(UTC) + case.expires_in)

    result = await asset_component._read_cached_file_if_valid(cached_asset, expired_ok=case.expired_ok)

    assert result == case.expected_bytes
