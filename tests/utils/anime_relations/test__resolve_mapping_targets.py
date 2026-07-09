from dataclasses import dataclass

import pytest

from constants import MappingOverrideMode
from utils.anime_relations import AnimeRelations

ALWAYS = MappingOverrideMode.ALWAYS
IF_MISSING = MappingOverrideMode.IF_MISSING


@dataclass
class Case:
    id: str
    episode_number: int
    source_map: dict
    expected_result: list   # [(target_episode, part, part_ceiling, is_strict_override)]


CASES = [
    # anibridge (mode None) -> not a strict override
    Case(id="one-to-one, anibridge",
         episode_number=3, source_map={(1, 12): [(1, 12, 1, None)]},
         expected_result=[(3, None, None, False)]),
    # an ALWAYS override flags the target as strict
    Case(id="one-to-one, ALWAYS override is strict",
         episode_number=3, source_map={(1, 12): [(1, 12, 1, ALWAYS)]},
         expected_result=[(3, None, None, True)]),
    # an IF_MISSING override is not strict
    Case(id="one-to-one, IF_MISSING override is not strict",
         episode_number=3, source_map={(1, 12): [(1, 12, 1, IF_MISSING)]},
         expected_result=[(3, None, None, False)]),
    # positive step > 1 collapses source eps onto one target with part info
    Case(id="collapse positive step (ep 1)",
         episode_number=1, source_map={(1, 2): [(5, 5, 2, None)]},
         expected_result=[(5, 1, 2, False)]),
    Case(id="collapse positive step (ep 2), strict",
         episode_number=2, source_map={(1, 2): [(5, 5, 2, ALWAYS)]},
         expected_result=[(5, 2, 2, True)]),
    # negative step expands one source ep into several targets (no parts)
    Case(id="expand negative step",
         episode_number=1, source_map={(1, 3): [(1, 6, -2, None)]},
         expected_result=[(1, None, None, False), (2, None, None, False)]),
    # step 0 targets are skipped
    Case(id="step zero is skipped",
         episode_number=3, source_map={(1, 12): [(1, 12, 0, None)]},
         expected_result=[]),
    # episode below the source range yields nothing
    Case(id="episode below source range",
         episode_number=3, source_map={(5, 12): [(1, 8, 1, None)]},
         expected_result=[]),
    # target beyond the target upper bound is dropped
    Case(id="target past upper bound is excluded",
         episode_number=20, source_map={(1, 24): [(1, 15, 1, None)]},
         expected_result=[]),
    # multiple target ranges each contribute a target
    Case(id="multiple target ranges",
         episode_number=1, source_map={(1, 24): [(1, 15, 1, None), (17, 22, 1, None)]},
         expected_result=[(1, None, None, False), (17, None, None, False)]),
    # the strict flag is per-target, not per-call
    Case(id="mixed modes flag targets independently",
         episode_number=1, source_map={(1, 24): [(1, 15, 1, None), (1, 15, 1, ALWAYS)]},
         expected_result=[(1, None, None, False), (1, None, None, True)]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__resolve_mapping_targets(case: Case):
    assert AnimeRelations._resolve_mapping_targets(case.episode_number, case.source_map) == case.expected_result
