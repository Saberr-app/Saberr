from dataclasses import dataclass
from urllib.parse import quote

import pytest

_ANILIST = "https://s4.anilist.co/file/anilistcdn/media/cover.png"
_FETCH = "services.static_files_service.StaticFilesService.get_arbitrary_file"


@dataclass
class Case:
    id: str
    preexisting_bytes: bytes | None   # seed the file on disk first; None means missing
    fetched_bytes: bytes              # what the network fetch would return
    expected_result: bytes            # bytes the returned path holds
    expect_fetch: bool


CASES = [
    Case(id="fetches and stores when missing",
         preexisting_bytes=None, fetched_bytes=b"img", expected_result=b"img", expect_fetch=True),
    Case(id="serves existing fresh file without refetch",
         preexisting_bytes=b"existing", fetched_bytes=b"img", expected_result=b"existing", expect_fetch=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_file_path_for_encoded_external_image_url(case: Case, image_component, mocker):
    fetch = mocker.patch(_FETCH, return_value=case.fetched_bytes)
    if case.preexisting_bytes is not None:
        path = image_component._build_image_file_path(_ANILIST)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(case.preexisting_bytes)  # fresh mtime -> not past REFETCH_AFTER

    result = await image_component.get_file_path_for_encoded_external_image_url(quote(_ANILIST, safe=""))

    assert result.read_bytes() == case.expected_result
    if case.expect_fetch:
        fetch.assert_awaited_once_with(_ANILIST)
    else:
        fetch.assert_not_awaited()
