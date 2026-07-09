from dataclasses import dataclass

import pytest

from constants import CachedAssetType

URL = "https://example.com/a.png"
_TYPE = CachedAssetType.OTHER


@dataclass
class Case:
    id: str
    first_bytes: bytes               # static-files service return for the priming fetch
    second_bytes: bytes | None       # return after re-priming; None means no second call at all
    force_fetch: bool                # passed to the second get_asset_data call
    expected_result: bytes           # bytes returned by the second (asserted) call
    expected_fetch_count: int        # total get_arbitrary_file awaits
    expect_persisted: bool = False   # read row + file back when first call persists fresh


CASES = [
    Case(id="fetches, persists and returns when not cached",
         first_bytes=b"image-bytes", second_bytes=None, force_fetch=False,
         expected_result=b"image-bytes", expected_fetch_count=1, expect_persisted=True),
    Case(id="returns cached without refetching when valid",
         first_bytes=b"v1", second_bytes=b"v2", force_fetch=False,
         expected_result=b"v1", expected_fetch_count=1),
    Case(id="force fetch refetches and updates",
         first_bytes=b"v1", second_bytes=b"v2", force_fetch=True,
         expected_result=b"v2", expected_fetch_count=2),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_asset_data(case: Case, asset_component, fake_cached_asset_store):
    fetch = asset_component._static_files_service.get_arbitrary_file
    fetch.return_value = case.first_bytes

    if case.second_bytes is None:
        data = await asset_component.get_asset_data(url=URL, asset_type=_TYPE)
    else:
        await asset_component.get_asset_data(url=URL, asset_type=_TYPE)
        fetch.return_value = case.second_bytes
        data = await asset_component.get_asset_data(url=URL, asset_type=_TYPE, force_fetch=case.force_fetch)

    assert data == case.expected_result
    assert fetch.await_count == case.expected_fetch_count

    if case.expect_persisted:
        fetch.assert_awaited_once_with(URL)
        assert len(fake_cached_asset_store) == 1
        asset = next(iter(fake_cached_asset_store.values()))
        assert asset_component._build_asset_file_path(asset.asset_filename, asset.asset_type).read_bytes() \
            == case.expected_result
