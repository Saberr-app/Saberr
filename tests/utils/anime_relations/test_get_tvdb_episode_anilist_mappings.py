from dataclasses import dataclass, field

import pytest

from constants import MappingOverrideMode
from dto.orm_models import MappingOverride
from dto.tvdb import TVDBEpisodeAnilistMapping

ALWAYS = MappingOverrideMode.ALWAYS
IF_MISSING = MappingOverrideMode.IF_MISSING


def mapping(anilist_id, episode_number, part=None, part_ceiling=None):
    return TVDBEpisodeAnilistMapping(anilist_id=anilist_id, episode_number=episode_number,
                                     part=part, part_ceiling=part_ceiling)


def override(mode, *, anilist_id=777, anilist_from=1, anilist_to=None, tvdb_series_id=5000,
             tvdb_season_number=1, tvdb_from=1, tvdb_to=None, granularity=1):
    return MappingOverride(anilist_id=anilist_id,
                           anilist_episode_number_from=anilist_from, anilist_episode_number_to=anilist_to,
                           tvdb_series_id=tvdb_series_id, tvdb_season_number=tvdb_season_number,
                           tvdb_episode_number_from=tvdb_from, tvdb_episode_number_to=tvdb_to,
                           granularity=granularity, mode=mode)


@dataclass
class Case:
    id: str
    series_id: int
    season_number: int
    episode_number: int
    expected_result: list[TVDBEpisodeAnilistMapping]
    tvdb_anilist: dict = field(default_factory=dict)
    overrides: list = field(default_factory=list)


CASES = [
    Case(id="empty when no mappings loaded",
         series_id=5000, season_number=1, episode_number=1, expected_result=[]),
    Case(id="empty for unknown series key (wrong season)",
         tvdb_anilist={(5000, 1): {300: {(1, 12): [(1, 12, 1, None)]}}},
         series_id=5000, season_number=2, episode_number=1, expected_result=[]),
    Case(id="empty for unknown series key (wrong series)",
         tvdb_anilist={(5000, 1): {300: {(1, 12): [(1, 12, 1, None)]}}},
         series_id=9999, season_number=1, episode_number=1, expected_result=[]),
    Case(id="one-to-one mapping",
         tvdb_anilist={(5000, 1): {300: {(1, 12): [(1, 12, 1, None)]}}},
         series_id=5000, season_number=1, episode_number=4, expected_result=[mapping(300, 4)]),
    Case(id="collapse with parts positive step (ep 1)",
         tvdb_anilist={(5000, 1): {300: {(1, 3): [(7, 7, 3, None)]}}},
         series_id=5000, season_number=1, episode_number=1,
         expected_result=[mapping(300, 7, part=1, part_ceiling=3)]),
    Case(id="collapse with parts positive step (ep 3)",
         tvdb_anilist={(5000, 1): {300: {(1, 3): [(7, 7, 3, None)]}}},
         series_id=5000, season_number=1, episode_number=3,
         expected_result=[mapping(300, 7, part=3, part_ceiling=3)]),
    Case(id="expand negative step",
         tvdb_anilist={(5000, 1): {300: {(1, 3): [(1, 6, -2, None)]}}},
         series_id=5000, season_number=1, episode_number=2,
         expected_result=[mapping(300, 3), mapping(300, 4)]),
    Case(id="out of range returns empty",
         tvdb_anilist={(5000, 1): {300: {(1, 12): [(1, 12, 1, None)]}}},
         series_id=5000, season_number=1, episode_number=99, expected_result=[]),
    Case(id="highest anilist id wins when several match",
         tvdb_anilist={(5000, 1): {
             300: {(1, 12): [(1, 12, 1, None)]},
             200: {(1, 12): [(50, 61, 1, None)]},
         }},
         series_id=5000, season_number=1, episode_number=4, expected_result=[mapping(300, 4)]),
    Case(id="falls through to lower anilist id when higher does not match",
         tvdb_anilist={(5000, 1): {
             300: {(1, 12): [(1, 12, 1, None)]},
             200: {(13, 24): [(1, 12, 1, None)]},
         }},
         series_id=5000, season_number=1, episode_number=14, expected_result=[mapping(200, 2)]),
    # --- user overrides ---
    Case(id="ALWAYS override wins over anibridge",
         tvdb_anilist={(5000, 1): {300: {(1, 12): [(1, 12, 1, None)]}}},
         overrides=[override(ALWAYS, anilist_id=777)],
         series_id=5000, season_number=1, episode_number=4, expected_result=[mapping(777, 4)]),
    Case(id="IF_MISSING override ignored when anibridge present",
         tvdb_anilist={(5000, 1): {300: {(1, 12): [(1, 12, 1, None)]}}},
         overrides=[override(IF_MISSING, anilist_id=777)],
         series_id=5000, season_number=1, episode_number=4, expected_result=[mapping(300, 4)]),
    Case(id="IF_MISSING override used when anibridge missing",
         overrides=[override(IF_MISSING, anilist_id=777)],
         series_id=5000, season_number=1, episode_number=4, expected_result=[mapping(777, 4)]),
    Case(id="ALWAYS override used when anibridge missing",
         overrides=[override(ALWAYS, anilist_id=777)],
         series_id=5000, season_number=1, episode_number=4, expected_result=[mapping(777, 4)]),
    # an override for a different season must not be applied to this one
    Case(id="override for another season is not applied",
         tvdb_anilist={(5000, 1): {300: {(1, 12): [(1, 12, 1, None)]}}},
         overrides=[override(ALWAYS, anilist_id=777, tvdb_season_number=2)],
         series_id=5000, season_number=1, episode_number=4, expected_result=[mapping(300, 4)]),
    # the override does not cover the requested episode, so anibridge stands
    Case(id="non-matching ALWAYS override does not suppress anibridge",
         tvdb_anilist={(5000, 1): {300: {(1, 12): [(1, 12, 1, None)]}}},
         overrides=[override(ALWAYS, anilist_id=777, tvdb_from=8, tvdb_to=10)],
         series_id=5000, season_number=1, episode_number=4, expected_result=[mapping(300, 4)]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_tvdb_episode_anilist_mappings(case: Case, make_relations, mock_overrides):
    mock_overrides(case.overrides)
    ar = make_relations(tvdb_anilist=case.tvdb_anilist)
    result = await ar.get_tvdb_episode_anilist_mappings(
        case.series_id, case.season_number, case.episode_number)
    assert result == case.expected_result
