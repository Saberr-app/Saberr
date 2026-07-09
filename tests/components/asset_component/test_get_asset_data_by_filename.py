from dataclasses import dataclass

import pytest

from constants import CachedAssetType

URL = "https://example.com/a.png"
_TYPE = CachedAssetType.OTHER


@dataclass
class Case:
    id: str
    lookup_missing: bool          # call with a filename that isn't in the db
    primed_bytes: bytes | None    # bytes the priming fetch returns when seeding
    expected_result: bytes | None


CASES = [
    Case(id="returns none when filename not in db",
         lookup_missing=True, primed_bytes=None, expected_result=None),
    Case(id="returns cached bytes when valid",
         lookup_missing=False, primed_bytes=b"data", expected_result=b"data"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_asset_data_by_filename(case: Case, asset_component, fake_cached_asset_store):
    if case.lookup_missing:
        assert await asset_component.get_asset_data_by_filename(
            asset_filename="missing.png", asset_type=_TYPE) is None
        return

    asset_component._static_files_service.get_arbitrary_file.return_value = case.primed_bytes
    await asset_component.get_asset_data(url=URL, asset_type=_TYPE)
    asset = next(iter(fake_cached_asset_store.values()))

    data = await asset_component.get_asset_data_by_filename(asset_filename=asset.asset_filename,
                                                            asset_type=_TYPE)

    assert data == case.expected_result
