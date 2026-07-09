from dataclasses import dataclass

import pytest

from constants import TorrentDownloadStatus as Status

_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"


@dataclass
class Case:
    id: str
    has_newer_active: bool  # what the repo's "active downloads for this episode/part" lookup returns
    expected_remaining: bool


CASES = [
    Case(id="passes through when not superseded", has_newer_active=False, expected_remaining=True),
    Case(id="superseded by newer active download is discarded", has_newer_active=True,
         expected_remaining=False),
    Case(id="no competing download leaves it active", has_newer_active=False, expected_remaining=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test__filter_out_and_update_superseded_downloads(case: Case, make_torrent_download_component,
                                                           make_download_chain, mocker):
    download = make_download_chain(status=Status.DOWNLOADING)
    mocker.patch(f"{_REPO}.get_active_downloads_by_episode_id_and_part",
                 return_value=[1] if case.has_newer_active else [])
    repo_update = mocker.patch(f"{_REPO}.update_downloads")

    component = make_torrent_download_component()
    remaining = await component._filter_out_and_update_superseded_downloads(downloads=[download])

    superseded_ids = [download.id] if not case.expected_remaining else []
    assert [d.id for d in remaining] == ([download.id] if case.expected_remaining else [])
    # the discard update always runs; its id list is the superseded set
    assert repo_update.await_args.kwargs["download_ids"] == superseded_ids
    assert repo_update.await_args.kwargs["status"] == Status.DISCARDED
