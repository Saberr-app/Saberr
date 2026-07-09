from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from common.exceptions import NotFoundException
from components.api_components.download_api_component import DownloadAPIComponent

_DC = "components.operational_components.torrent_download_component.TorrentDownloadComponent"
_TC = "components.operational_components.torrent_component.TorrentComponent"
_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"


def _download():
    torrent = SimpleNamespace(id=10, tracked_anime_episode_id=5, episode_part=0, episode_part_ceiling=0,
                              tracked_anime_episode=SimpleNamespace(tracked_anime=SimpleNamespace(profile="P")))
    return SimpleNamespace(id=1, created_at=None, torrent=torrent)


@dataclass
class Case:
    id: str
    download: object
    newer_downloads: list
    best_candidate: object
    expected_superseded: bool = False
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="missing download raises not found",
         download=None, newer_downloads=[], best_candidate=None,
         expected_exception=NotFoundException),
    Case(id="no newer downloads means not superseded",
         download=_download(), newer_downloads=[], best_candidate=None,
         expected_superseded=False),
    # a newer download whose torrent beats the current one -> superseded
    Case(id="better newer candidate supersedes",
         download=_download(), newer_downloads=[SimpleNamespace(id=2)],
         best_candidate=SimpleNamespace(id=99), expected_superseded=True),
    # the current download's own torrent is still the best -> not superseded
    Case(id="current torrent still best is not superseded",
         download=_download(), newer_downloads=[SimpleNamespace(id=2)],
         best_candidate=SimpleNamespace(id=1), expected_superseded=False),
    Case(id="no best candidate is not superseded",
         download=_download(), newer_downloads=[SimpleNamespace(id=2)],
         best_candidate=None, expected_superseded=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_check_download_retry(case: Case, mocker):
    mocker.patch(f"{_DC}.get_download", return_value=case.download)
    mocker.patch(f"{_REPO}.get_active_downloads_by_episode_id_and_part", return_value=case.newer_downloads)
    mocker.patch(f"{_TC}.get_best_torrent_for_episode", return_value=case.best_candidate)

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await DownloadAPIComponent().check_download_retry(download_id=1)
        return

    result = await DownloadAPIComponent().check_download_retry(download_id=1)
    assert result.superseded is case.expected_superseded
