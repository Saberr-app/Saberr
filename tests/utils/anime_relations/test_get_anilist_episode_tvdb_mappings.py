from dataclasses import dataclass, field

import pytest

from constants import MappingOverrideMode
from dto.orm_models import MappingOverride
from dto.tvdb import AnilistEpisodeTVDBMapping

ALWAYS = MappingOverrideMode.ALWAYS
IF_MISSING = MappingOverrideMode.IF_MISSING


def mapping(series_id, season_number, episode_number, part=None, part_ceiling=None):
    return AnilistEpisodeTVDBMapping(series_id=series_id, season_number=season_number,
                                     episode_number=episode_number, part=part, part_ceiling=part_ceiling)


def override(mode, *, anilist_id=100, anilist_from=1, anilist_to=None, tvdb_series_id=8000,
             tvdb_season_number=1, tvdb_from=1, tvdb_to=None, granularity=1):
    return MappingOverride(anilist_id=anilist_id,
                           anilist_episode_number_from=anilist_from, anilist_episode_number_to=anilist_to,
                           tvdb_series_id=tvdb_series_id, tvdb_season_number=tvdb_season_number,
                           tvdb_episode_number_from=tvdb_from, tvdb_episode_number_to=tvdb_to,
                           granularity=granularity, mode=mode)


@dataclass
class Case:
    id: str
    anilist_id: int
    episode_number: int
    expected_result: list[AnilistEpisodeTVDBMapping]
    anilist_tvdb: dict = field(default_factory=dict)
    overrides: list = field(default_factory=list)


CASES = [
    Case(id="empty when no mappings loaded", anilist_id=100, episode_number=1, expected_result=[]),
    Case(id="empty for unknown anilist id",
         anilist_tvdb={100: {(5000, 1): {(1, 12): [(1, 12, 1, None)]}}},
         anilist_id=999, episode_number=1, expected_result=[]),
    Case(id="one-to-one mapping",
         anilist_tvdb={100: {(5000, 1): {(1, 12): [(1, 12, 1, None)]}}},
         anilist_id=100, episode_number=3, expected_result=[mapping(5000, 1, 3)]),
    # source eps 13-24 map onto target eps 1-12
    Case(id="season offset mapping",
         anilist_tvdb={100: {(5000, 2): {(13, 24): [(1, 12, 1, None)]}}},
         anilist_id=100, episode_number=14, expected_result=[mapping(5000, 2, 2)]),
    # 2 source eps collapse onto target ep 5 -> part info
    Case(id="collapse with parts positive step (ep 1)",
         anilist_tvdb={100: {(5000, 1): {(1, 2): [(5, 5, 2, None)]}}},
         anilist_id=100, episode_number=1,
         expected_result=[mapping(5000, 1, 5, part=1, part_ceiling=2)]),
    Case(id="collapse with parts positive step (ep 2)",
         anilist_tvdb={100: {(5000, 1): {(1, 2): [(5, 5, 2, None)]}}},
         anilist_id=100, episode_number=2,
         expected_result=[mapping(5000, 1, 5, part=2, part_ceiling=2)]),
    # 1 source ep expands to 2 target eps (no parts)
    Case(id="expand negative step (ep 1)",
         anilist_tvdb={100: {(5000, 1): {(1, 3): [(1, 6, -2, None)]}}},
         anilist_id=100, episode_number=1,
         expected_result=[mapping(5000, 1, 1), mapping(5000, 1, 2)]),
    Case(id="expand negative step (ep 3)",
         anilist_tvdb={100: {(5000, 1): {(1, 3): [(1, 6, -2, None)]}}},
         anilist_id=100, episode_number=3,
         expected_result=[mapping(5000, 1, 5), mapping(5000, 1, 6)]),
    Case(id="multiple target ranges",
         anilist_tvdb={100: {(5000, 1): {(1, 24): [(1, 15, 1, None), (17, 22, 1, None), (24, 26, 1, None)]}}},
         anilist_id=100, episode_number=1,
         expected_result=[mapping(5000, 1, 1), mapping(5000, 1, 17), mapping(5000, 1, 24)]),
    # ep 7 -> 7 (in 1-15); 23 would be >22 and 30 >26, both excluded
    Case(id="target range upper bound excludes out-of-range targets",
         anilist_tvdb={100: {(5000, 1): {(1, 24): [(1, 15, 1, None), (17, 22, 1, None), (24, 26, 1, None)]}}},
         anilist_id=100, episode_number=7, expected_result=[mapping(5000, 1, 7)]),
    # ep 16 -> every target range is exhausted -> empty
    Case(id="all target ranges exhausted -> empty",
         anilist_tvdb={100: {(5000, 1): {(1, 24): [(1, 15, 1, None), (17, 22, 1, None), (24, 26, 1, None)]}}},
         anilist_id=100, episode_number=16, expected_result=[]),
    Case(id="episode below source range returns empty",
         anilist_tvdb={100: {(5000, 1): {(5, 12): [(1, 8, 1, None)]}}},
         anilist_id=100, episode_number=3, expected_result=[]),
    # source end None -> no upper bound on the source episode
    Case(id="open-ended source range",
         anilist_tvdb={100: {(5000, 1): {(1, None): [(1, None, 1, None)]}}},
         anilist_id=100, episode_number=999, expected_result=[mapping(5000, 1, 999)]),
    # both keys cover ep 3, but the higher (series_id, season) is selected
    Case(id="highest series key wins when several match",
         anilist_tvdb={100: {
             (200, 1): {(1, 12): [(1, 12, 1, None)]},
             (100, 1): {(1, 12): [(99, 110, 1, None)]},
         }},
         anilist_id=100, episode_number=3, expected_result=[mapping(200, 1, 3)]),
    # ep 15 isn't covered by (200, 1); resolution continues to (100, 1)
    Case(id="falls through to lower series key when higher does not match",
         anilist_tvdb={100: {
             (200, 1): {(1, 12): [(1, 12, 1, None)]},
             (100, 1): {(13, 24): [(1, 12, 1, None)]},
         }},
         anilist_id=100, episode_number=15, expected_result=[mapping(100, 1, 3)]),
    # --- user overrides ---
    # an ALWAYS override takes precedence over the anibridge mapping for the same episode
    Case(id="ALWAYS override wins over anibridge",
         anilist_tvdb={100: {(5000, 1): {(1, 12): [(1, 12, 1, None)]}}},
         overrides=[override(ALWAYS, tvdb_series_id=8000)],
         anilist_id=100, episode_number=3, expected_result=[mapping(8000, 1, 3)]),
    # an IF_MISSING override is ignored while the anibridge has a mapping
    Case(id="IF_MISSING override ignored when anibridge present",
         anilist_tvdb={100: {(5000, 1): {(1, 12): [(1, 12, 1, None)]}}},
         overrides=[override(IF_MISSING, tvdb_series_id=8000)],
         anilist_id=100, episode_number=3, expected_result=[mapping(5000, 1, 3)]),
    # an IF_MISSING override fills in when the anibridge has nothing
    Case(id="IF_MISSING override used when anibridge missing",
         overrides=[override(IF_MISSING, tvdb_series_id=8000)],
         anilist_id=100, episode_number=3, expected_result=[mapping(8000, 1, 3)]),
    Case(id="ALWAYS override used when anibridge missing",
         overrides=[override(ALWAYS, tvdb_series_id=8000)],
         anilist_id=100, episode_number=3, expected_result=[mapping(8000, 1, 3)]),
    # the override exists but does not cover the requested episode, so it must not suppress anibridge
    Case(id="non-matching ALWAYS override does not suppress anibridge",
         anilist_tvdb={100: {(5000, 1): {(1, 12): [(1, 12, 1, None)]}}},
         overrides=[override(ALWAYS, anilist_from=5, anilist_to=10, tvdb_series_id=8000, tvdb_from=5)],
         anilist_id=100, episode_number=3, expected_result=[mapping(5000, 1, 3)]),
    # granularity carries through the override path (2 source eps collapse onto one target)
    Case(id="ALWAYS override honours granularity",
         overrides=[override(ALWAYS, anilist_from=1, anilist_to=2, tvdb_series_id=8000,
                             tvdb_from=5, tvdb_to=5, granularity=2)],
         anilist_id=100, episode_number=1,
         expected_result=[mapping(8000, 1, 5, part=1, part_ceiling=2)]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_anilist_episode_tvdb_mappings(case: Case, make_relations, mock_overrides):
    mock_overrides(case.overrides)
    ar = make_relations(anilist_tvdb=case.anilist_tvdb)
    result = await ar.get_anilist_episode_tvdb_mappings(case.anilist_id, case.episode_number)
    assert result == case.expected_result
