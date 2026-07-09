from dataclasses import dataclass

import pytest

_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"


@dataclass
class Case:
    id: str
    magnet_hashes: list[str]
    load_relations: bool


CASES = [
    Case(id="loads relations by default", magnet_hashes=["h1", "h2"], load_relations=True),
    Case(id="relations disabled", magnet_hashes=["h3"], load_relations=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_downloads_by_hashes(case: Case, make_torrent_download_component, mocker):
    sentinel = [object()]
    repo = mocker.patch(f"{_REPO}.get_downloads_by_hashes", return_value=sentinel)

    result = await make_torrent_download_component().get_downloads_by_hashes(
        magnet_hashes=case.magnet_hashes, load_relations=case.load_relations)

    assert result is sentinel
    repo.assert_awaited_once_with(magnet_hashes=case.magnet_hashes, load_relations=case.load_relations)
