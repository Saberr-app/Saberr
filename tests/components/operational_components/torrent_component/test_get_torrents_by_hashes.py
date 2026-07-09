from dataclasses import dataclass, field
from unittest.mock import MagicMock

import pytest

from system import UNSET

_REPO = "repositories.torrent_repositories.torrent_repo.TorrentRepo"


@dataclass
class Case:
    id: str
    call_kwargs: dict = field(default_factory=dict)
    expected_discarded: object = None       # default: include discarded (discarded=None)
    expected_parent_torrent_id: object = UNSET   # default: any parent (parent_torrent_id=UNSET)


CASES = [
    Case(id="defaults include discarded and any parent",
         expected_discarded=None, expected_parent_torrent_id=UNSET),
    Case(id="exclude_discarded passes discarded=False",
         call_kwargs=dict(exclude_discarded=True), expected_discarded=False),
    Case(id="parent_torrent_only passes parent_torrent_id=None",
         call_kwargs=dict(parent_torrent_only=True), expected_parent_torrent_id=None),
    Case(id="both toggles on",
         call_kwargs=dict(exclude_discarded=True, parent_torrent_only=True),
         expected_discarded=False, expected_parent_torrent_id=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_torrents_by_hashes(case: Case, make_component, mocker):
    result = [MagicMock()]
    repo = mocker.patch(f"{_REPO}.get_torrents_by_hashes", return_value=result)

    returned = await make_component().get_torrents_by_hashes(magnet_hashes=["h1", "h2"], **case.call_kwargs)

    assert returned is result
    passed = repo.await_args.kwargs
    assert set(passed["magnet_hashes"]) == {"h1", "h2"}
    assert passed["discarded"] is case.expected_discarded
    assert passed["parent_torrent_id"] is case.expected_parent_torrent_id
    assert passed["load_relations"] is True
