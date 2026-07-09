from dataclasses import dataclass

import pytest

from constants import CachedAssetType

URL = "https://example.com/x.png"
_TYPE = CachedAssetType.OTHER


@dataclass
class Case:
    id: str
    prime_url: str | None       # if set, get_asset_data is run for this url first to cache it
    lookup_url: str             # url passed to get_asset_path
    fetch_if_not_exists: bool
    expect_none: bool           # path should be None
    expect_fetch_awaited: bool  # the static-files fetch should have been awaited


CASES = [
    Case(id="returns none when not cached and no fetch",
         prime_url=None, lookup_url=URL, fetch_if_not_exists=False,
         expect_none=True, expect_fetch_awaited=False),
    Case(id="returns base-path-prefixed path when cached",
         prime_url=URL, lookup_url=URL, fetch_if_not_exists=False,
         expect_none=False, expect_fetch_awaited=False),
    Case(id="fetches when requested and missing",
         prime_url=None, lookup_url="https://example.com/y.png", fetch_if_not_exists=True,
         expect_none=False, expect_fetch_awaited=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_asset_path(case: Case, asset_component, tmp_path):
    asset_component._static_files_service.get_arbitrary_file.return_value = b"b"
    if case.prime_url is not None:
        await asset_component.get_asset_data(url=case.prime_url, asset_type=_TYPE)

    path = await asset_component.get_asset_path(url=case.lookup_url, asset_type=_TYPE,
                                                fetch_if_not_exists=case.fetch_if_not_exists)

    if case.expect_none:
        assert path is None
    else:
        assert path is not None
        assert str(path).startswith(str(tmp_path))
        assert str(path).endswith(".png")

    if case.expect_fetch_awaited:
        asset_component._static_files_service.get_arbitrary_file.assert_awaited()
