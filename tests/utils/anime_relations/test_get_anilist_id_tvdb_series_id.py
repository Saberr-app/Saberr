from dataclasses import dataclass, field

import pytest

from constants import MappingOverrideMode
from dto.orm_models import MappingOverride

ALWAYS = MappingOverrideMode.ALWAYS
IF_MISSING = MappingOverrideMode.IF_MISSING


def override(mode, *, anilist_id=100, tvdb_series_id=8000, tvdb_season_number=1):
    return MappingOverride(anilist_id=anilist_id,
                           anilist_episode_number_from=1, anilist_episode_number_to=None,
                           tvdb_series_id=tvdb_series_id, tvdb_season_number=tvdb_season_number,
                           tvdb_episode_number_from=1, tvdb_episode_number_to=None,
                           granularity=1, mode=mode)


@dataclass
class Case:
    id: str
    anilist_id: int
    expected_result: int | None
    anilist_tvdb: dict = field(default_factory=dict)
    overrides: list = field(default_factory=list)


CASES = [
    Case(id="none when no mappings loaded", anilist_id=100, expected_result=None),
    Case(id="none for unknown anilist id",
         anilist_tvdb={100: {(5000, 1): {}}}, anilist_id=999, expected_result=None),
    Case(id="none when anilist id maps to nothing",
         anilist_tvdb={100: {}}, anilist_id=100, expected_result=None),
    Case(id="single series returned",
         anilist_tvdb={100: {(5000, 1): {}}}, anilist_id=100, expected_result=5000),
    Case(id="lowest season number wins",
         anilist_tvdb={100: {(5000, 2): {}, (6000, 1): {}}}, anilist_id=100, expected_result=6000),
    # season 0 (specials) is pushed to the back via float('inf')
    Case(id="season zero is deprioritized",
         anilist_tvdb={100: {(5000, 0): {}, (6000, 3): {}}}, anilist_id=100, expected_result=6000),
    Case(id="season zero used when only option",
         anilist_tvdb={100: {(7000, 0): {}}}, anilist_id=100, expected_result=7000),
    Case(id="ties broken by lower series id",
         anilist_tvdb={100: {(7000, 1): {}, (3000, 1): {}}}, anilist_id=100, expected_result=3000),
    # --- user overrides ---
    # an ALWAYS override forces the series id even when the anibridge has one
    Case(id="ALWAYS override wins over anibridge",
         anilist_tvdb={100: {(5000, 1): {}}},
         overrides=[override(ALWAYS, tvdb_series_id=8000)],
         anilist_id=100, expected_result=8000),
    # an IF_MISSING override is ignored while the anibridge resolves a series
    Case(id="IF_MISSING override ignored when anibridge present",
         anilist_tvdb={100: {(5000, 1): {}}},
         overrides=[override(IF_MISSING, tvdb_series_id=8000)],
         anilist_id=100, expected_result=5000),
    # an IF_MISSING override fills in when the anibridge has no series
    Case(id="IF_MISSING override used when anibridge missing",
         overrides=[override(IF_MISSING, tvdb_series_id=8000)],
         anilist_id=100, expected_result=8000),
    Case(id="ALWAYS override used when anibridge missing",
         overrides=[override(ALWAYS, tvdb_series_id=8000)],
         anilist_id=100, expected_result=8000),
    # override season priority mirrors anibridge: lowest non-zero season wins
    Case(id="override lowest season wins",
         overrides=[override(ALWAYS, tvdb_series_id=8000, tvdb_season_number=2),
                    override(ALWAYS, tvdb_series_id=9000, tvdb_season_number=1)],
         anilist_id=100, expected_result=9000),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_anilist_id_tvdb_series_id(case: Case, make_relations, mock_overrides):
    mock_overrides(case.overrides)
    ar = make_relations(anilist_tvdb=case.anilist_tvdb)
    assert await ar.get_anilist_id_tvdb_series_id(case.anilist_id) == case.expected_result
