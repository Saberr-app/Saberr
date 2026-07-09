from dataclasses import dataclass

import pytest


@dataclass
class Case:
    id: str
    url: str
    fetched_bytes: bytes
    expected_result: bytes


CASES = [
    Case(id="returns the static-files bytes fetched for the url",
         url="http://example.com/a.png", fetched_bytes=b"image-data", expected_result=b"image-data"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test__fetch_asset_bytes(case: Case, asset_component):
    asset_component._static_files_service.get_arbitrary_file.return_value = case.fetched_bytes

    result = await asset_component._fetch_asset_bytes(case.url)

    assert result == case.expected_result
    asset_component._static_files_service.get_arbitrary_file.assert_awaited_once_with(case.url)
