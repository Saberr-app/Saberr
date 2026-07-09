from dataclasses import dataclass, field

import pytest

from constants import ReleaseCriteriaProperty as RCP

_REPO = "repositories.torrent_repositories.torrent_repo.TorrentRepo"


@dataclass
class Case:
    id: str
    profile_kwargs: dict = field(default_factory=dict)
    torrents: list = field(default_factory=list)     # list of make_candidate kwargs (profile injected by runner)
    episode_ids: list = field(default_factory=lambda: [1])
    scope_hashes: set | None = None
    expected_selected: set = field(default_factory=set)
    expected_dismissed: dict | None = None


CASES = [
    Case(id="single candidate is selected",
         torrents=[dict(magnet_hash="only")], expected_selected={"only"}, expected_dismissed={}),
    Case(id="dismissed torrent is reported not selected",
         profile_kwargs=dict(preferred_release_groups=["GroupB"]),
         torrents=[dict(magnet_hash="bad", release_group="GroupA")],
         expected_selected=set(), expected_dismissed={"bad": [RCP.RELEASE_GROUP]}),
    Case(id="version priority keeps the highest version",
         profile_kwargs=dict(priorities_sorted=[RCP.VERSION]),
         torrents=[dict(magnet_hash="v1", version_number=1), dict(magnet_hash="v2", version_number=2)],
         expected_selected={"v2"}),
    Case(id="release group preference ranking wins",
         profile_kwargs=dict(preferred_release_groups=["GroupA", "GroupB"], priorities_sorted=[RCP.RELEASE_GROUP]),
         torrents=[dict(magnet_hash="b", release_group="GroupB"), dict(magnet_hash="a", release_group="GroupA")],
         expected_selected={"a"}),
    Case(id="tie breaks on the highest sorted hash",
         torrents=[dict(magnet_hash="zzz"), dict(magnet_hash="aaa")], expected_selected={"zzz"}),
    Case(id="repack takes precedence over the hash tie-break",
         torrents=[dict(magnet_hash="aaa", repack_indicator=False),
                   dict(magnet_hash="zzz", repack_indicator=True)],
         expected_selected={"zzz"}),
    Case(id="accept_release_upgrades false keeps the existing download",
         profile_kwargs=dict(accept_release_upgrades=False, priorities_sorted=[RCP.VERSION]),
         torrents=[dict(magnet_hash="downloaded", version_number=1, active_download=True),
                   dict(magnet_hash="newer", version_number=2)],
         expected_selected={"downloaded"}),
    Case(id="scope filters out torrents without an active download",
         torrents=[dict(magnet_hash="in", episode_id=1), dict(magnet_hash="out", episode_id=2)],
         episode_ids=[1, 2], scope_hashes={"in"}, expected_selected={"in"}),
    Case(id="separate episodes are selected independently",
         torrents=[dict(magnet_hash="e1", episode_id=1), dict(magnet_hash="e2", episode_id=2)],
         episode_ids=[1, 2], expected_selected={"e1", "e2"}),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_determine_torrents_candidacy(case: Case, make_component, make_profile, make_candidate, mocker):
    profile = make_profile(**case.profile_kwargs)
    torrents = [make_candidate(profile=profile, **spec) for spec in case.torrents]
    mocker.patch(f"{_REPO}.get_torrents_by_tracked_anime_episode_ids", return_value=torrents)

    selected, dismissed = await make_component().determine_torrents_candidacy(
        episode_ids=case.episode_ids, scope_hashes=case.scope_hashes)

    assert selected == case.expected_selected
    if case.expected_dismissed is not None:
        assert dismissed == case.expected_dismissed
