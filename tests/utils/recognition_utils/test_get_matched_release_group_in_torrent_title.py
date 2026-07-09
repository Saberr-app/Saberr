from dataclasses import dataclass

import pytest

from utils.recognition_utils import get_matched_release_group_in_torrent_title


@dataclass
class Case:
    id: str
    title: str
    expected_name: str | None


CASES = [
    Case(id="erai-raws",
         title="[Erai-raws] Nippon Sangoku - 09 [540p AMZN WEB-DL AVC EAC3][MultiSub][7BBD7C88]",
         expected_name="Erai-raws"),
    Case(id="dkb",
         title="[DKB] Akane-banashi - S01E09 [1080p][HEVC x265 10bit][Multi-Subs][weekly]",
         expected_name="DKB"),
    Case(id="subsplease",
         title="[SubsPlease] Niwatori Fighter - 12 (1080p) [A651BA8D].mkv",
         expected_name="SubsPlease"),
    Case(id="judas",
         title="[Judas] NEEDY GIRL OVERDOSE - S01E09 [1080p][HEVC x265 10bit][Multi-Subs] (Weekly)",
         expected_name="Judas"),
    Case(id="asw",
         title="[ASW] Niwatori Fighter - 12 [1080p HEVC x265 10Bit][AAC]",
         expected_name="ASW"),
    # matching is prefix-based, independent of whether the title later parses
    Case(id="matches even when regex would not",
         title="[SubsPlease] MF Ghost (25-37) (1080p) [Batch]",
         expected_name="SubsPlease"),
    Case(id="unrecognized prefix returns none",
         title="[Unknown] Some Show - 01 (1080p)",
         expected_name=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_get_matched_release_group_in_torrent_title(case: Case, release_groups_map):
    matched = get_matched_release_group_in_torrent_title(case.title, release_groups_map)
    if case.expected_name is None:
        assert matched is None
    else:
        assert matched is not None
        assert matched.name == case.expected_name
