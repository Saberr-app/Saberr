from dataclasses import dataclass, field

import pytest

from constants import MappingOverrideMode
from dto.orm_models import MappingOverride
from utils.anime_relations import AnimeRelations

ALWAYS = MappingOverrideMode.ALWAYS
IF_MISSING = MappingOverrideMode.IF_MISSING


def override(*, mode=ALWAYS, anilist_id=100, anilist_from=1, anilist_to=12, tvdb_series_id=5000,
             tvdb_season_number=1, tvdb_from=1, tvdb_to=12, granularity=1):
    return MappingOverride(anilist_id=anilist_id,
                           anilist_episode_number_from=anilist_from, anilist_episode_number_to=anilist_to,
                           tvdb_series_id=tvdb_series_id, tvdb_season_number=tvdb_season_number,
                           tvdb_episode_number_from=tvdb_from, tvdb_episode_number_to=tvdb_to,
                           granularity=granularity, mode=mode)


@dataclass
class Case:
    id: str
    overrides: list
    expected_result: tuple   # (anilist_tvdb, tvdb_anilist)


CASES = [
    Case(id="empty overrides -> empty maps", overrides=[], expected_result=({}, {})),
    # a single override is shaped into both directions, with granularity and mode kept in the target tuple
    Case(id="single override, both directions",
         overrides=[override()],
         expected_result=(
             {100: {(5000, 1): {(1, 12): [(1, 12, 1, ALWAYS)]}}},
             {(5000, 1): {100: {(1, 12): [(1, 12, 1, ALWAYS)]}}},
         )),
    # granularity is authored anilist -> tvdb; the reverse direction gets its sign flipped when |g| >= 2
    Case(id="granularity is reversed for the tvdb -> anilist direction",
         overrides=[override(granularity=-2, mode=IF_MISSING)],
         expected_result=(
             {100: {(5000, 1): {(1, 12): [(1, 12, -2, IF_MISSING)]}}},
             {(5000, 1): {100: {(1, 12): [(1, 12, 2, IF_MISSING)]}}},
         )),
    # two overrides on the same series/anilist with disjoint ranges nest under the same keys
    Case(id="two overrides same series, different ranges and modes",
         overrides=[override(),
                    override(anilist_from=13, anilist_to=24, tvdb_from=13, tvdb_to=24, mode=IF_MISSING)],
         expected_result=(
             {100: {(5000, 1): {(1, 12): [(1, 12, 1, ALWAYS)],
                                (13, 24): [(13, 24, 1, IF_MISSING)]}}},
             {(5000, 1): {100: {(1, 12): [(1, 12, 1, ALWAYS)],
                                (13, 24): [(13, 24, 1, IF_MISSING)]}}},
         )),
    # overrides pointing the same anilist at different tvdb series/seasons nest as separate keys
    Case(id="one anilist mapped to two tvdb series",
         overrides=[override(tvdb_series_id=5000, tvdb_season_number=1),
                    override(tvdb_series_id=6000, tvdb_season_number=2)],
         expected_result=(
             {100: {(5000, 1): {(1, 12): [(1, 12, 1, ALWAYS)]},
                    (6000, 2): {(1, 12): [(1, 12, 1, ALWAYS)]}}},
             {(5000, 1): {100: {(1, 12): [(1, 12, 1, ALWAYS)]}},
              (6000, 2): {100: {(1, 12): [(1, 12, 1, ALWAYS)]}}},
         )),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__overrides_to_mappings(case: Case):
    assert AnimeRelations._overrides_to_mappings(case.overrides) == case.expected_result
