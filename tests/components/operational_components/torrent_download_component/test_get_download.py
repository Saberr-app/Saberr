from dataclasses import dataclass

import pytest

_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"


@dataclass
class Case:
    id: str
    download_id: int
    load_relations: bool


CASES = [
    Case(id="loads relations by default", download_id=7, load_relations=True),
    Case(id="relations disabled", download_id=9, load_relations=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_download(case: Case, make_torrent_download_component, mocker):
    sentinel = object()
    repo = mocker.patch(f"{_REPO}.get_download", return_value=sentinel)

    result = await make_torrent_download_component().get_download(download_id=case.download_id,
                                                                  load_relations=case.load_relations)

    assert result is sentinel
    repo.assert_awaited_once_with(download_id=case.download_id, load_relations=case.load_relations)
