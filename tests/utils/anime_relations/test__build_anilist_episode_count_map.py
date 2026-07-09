from dataclasses import dataclass

import pytest

from utils.anime_relations import AnimeRelations

# id:count:expires — expiry is far in the future, so every line is kept
_SOURCE = b"""2619:26:1963768208
2620:26:1963768208
2683:12:1963768208
2923:51:1963768208
3226:26:1963768208
3270:13:1963768208
3420:12:1963768208
3449:4:1963768208
3456:1:1963768208
"""

_EXPECTED = {
    2619: 26,
    2620: 26,
    2683: 12,
    2923: 51,
    3226: 26,
    3270: 13,
    3420: 12,
    3449: 4,
    3456: 1,
}


@dataclass
class Case:
    id: str
    source: bytes
    expected_result: dict


CASES = [
    Case(id="parses id:count lines, keeping unexpired entries", source=_SOURCE, expected_result=_EXPECTED),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__build_anilist_episode_count_map(case: Case):
    assert AnimeRelations._build_anilist_episode_count_map(case.source) == case.expected_result
