from dataclasses import dataclass, field

import pytest

from constants import TorrentDownloadStatus as Status

_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"


@dataclass
class Case:
    id: str
    kwargs: dict = field(default_factory=dict)
    expected_forwarded: dict = field(default_factory=dict)


CASES = [
    Case(id="defaults forwarded",
         kwargs={},
         expected_forwarded=dict(download_ids=None, statuses=None, offset=None, limit=None, load_relations=True)),
    Case(id="explicit args forwarded",
         kwargs=dict(download_ids=[1, 2], statuses=[Status.PENDING], offset=5, limit=10, load_relations=False),
         expected_forwarded=dict(download_ids=[1, 2], statuses=[Status.PENDING], offset=5, limit=10,
                                 load_relations=False)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_downloads(case: Case, make_torrent_download_component, mocker):
    sentinel = [object()]
    repo = mocker.patch(f"{_REPO}.get_downloads", return_value=sentinel)

    result = await make_torrent_download_component().get_downloads(**case.kwargs)

    assert result is sentinel
    forwarded = repo.await_args.kwargs
    for key, value in case.expected_forwarded.items():
        assert forwarded[key] == value
