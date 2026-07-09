from dataclasses import dataclass, field
from typing import Callable

import pytest

from constants import Encoding, Resolution, ReleaseCriteriaProperty as RCP
from components.operational_components.torrent_component import TorrentComponent


@dataclass
class Case:
    id: str
    build: Callable           # (make_profile, make_candidate) -> (candidates, profile)
    expected_hash: str | None


def _empty(make_profile, make_candidate):
    return [], make_profile()


def _single(make_profile, make_candidate):
    profile = make_profile()
    return [make_candidate(profile=profile, magnet_hash="only")], profile


def _version(make_profile, make_candidate):
    profile = make_profile(priorities_sorted=[RCP.VERSION])
    return ([make_candidate(profile=profile, magnet_hash="v1", version_number=1),
             make_candidate(profile=profile, magnet_hash="v2", version_number=2)], profile)


def _resolution(make_profile, make_candidate):
    profile = make_profile(priorities_sorted=[RCP.RESOLUTION],
                           preferred_resolutions=[Resolution.P1080, Resolution.P720])
    return ([make_candidate(profile=profile, magnet_hash="lo", resolution=Resolution.P720),
             make_candidate(profile=profile, magnet_hash="hi", resolution=Resolution.P1080)], profile)


def _release_group(make_profile, make_candidate):
    profile = make_profile(priorities_sorted=[RCP.RELEASE_GROUP],
                           preferred_release_groups=["GroupA", "GroupB"])
    return ([make_candidate(profile=profile, magnet_hash="b", release_group="GroupB"),
             make_candidate(profile=profile, magnet_hash="a", release_group="GroupA")], profile)


def _repack_tiebreak(make_profile, make_candidate):
    profile = make_profile()  # no priorities -> falls through to the repack/hash tiebreak
    return ([make_candidate(profile=profile, magnet_hash="aaa", repack_indicator=False),
             make_candidate(profile=profile, magnet_hash="bbb", repack_indicator=True)], profile)


def _hash_tiebreak(make_profile, make_candidate):
    profile = make_profile()
    return ([make_candidate(profile=profile, magnet_hash="h-a"),
             make_candidate(profile=profile, magnet_hash="h-b")], profile)


CASES = [
    Case(id="no candidates returns none", build=_empty, expected_hash=None),
    Case(id="single candidate returned as-is", build=_single, expected_hash="only"),
    Case(id="highest version wins", build=_version, expected_hash="v2"),
    Case(id="preferred resolution wins", build=_resolution, expected_hash="hi"),
    Case(id="preferred release group wins", build=_release_group, expected_hash="a"),
    Case(id="repack breaks an otherwise-tie", build=_repack_tiebreak, expected_hash="bbb"),
    Case(id="higher magnet hash breaks the final tie", build=_hash_tiebreak, expected_hash="h-b"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_get_best_torrent_for_episode(case: Case, make_profile, make_candidate):
    candidates, profile = case.build(make_profile, make_candidate)
    result = TorrentComponent.get_best_torrent_for_episode(candidates, profile)
    assert (result.magnet_hash if result else None) == case.expected_hash
