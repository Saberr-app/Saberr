from dataclasses import dataclass

import pytest

from utils.anime_relations import AnimeRelations

# only `tvdb_show:<series>:s<season>` targets are kept; mal/anidb/tmdb/imdb/tvdb_movie are ignored.
# there are no top-level `tvdb_show:` source ids here, so the reverse (tvdb->anilist) map is empty.
_SOURCE = b"""{
  "anilist:10471": {"mal:10471": {"1-3": "1-3"}, "tvdb_show:261387:s0": {"1-3": "1-3"}},
  "anilist:10477": {"anidb:7992:S": {"1": "1"}, "mal:10477": {"1": "1"}, "tvdb_show:214891:s0": {"1": "10"}},
  "anilist:10490": {"anidb:8348:R": {"1-12": "1-12"}, "mal:10490": {"1-12": "1-12"}, "tmdb_show:43270:s1": {"1-12": "1-12"}, "tvdb_show:249864:s1": {"1-12": "1-12"}},
  "anilist:10491": {"anidb:8350:R": {"1-4": "1-4"}, "mal:10491": {"1-4": "1-4"}, "tmdb_show:25760:s0": {"1-4": "7-10"}, "tvdb_show:79682:s0": {"1-4": "2-5"}},
  "anilist:10495": {"anidb:8353:R": {"1-12": "1-12"}, "mal:10495": {"1-12": "1-12"}, "tmdb_show:52891:s1": {"1-12": "1-12"}, "tvdb_show:250022:s1": {"1-12": "1-12"}},
  "anilist:10497": {"mal:10497": {"1-4": "1-4"}, "tmdb_show:35138:s0": {"1-4": "4-7"}, "tvdb_show:88161:s0": {"1-4": "5-8"}},
  "anilist:10500": {"anidb:8256:R": {"1": "1"}, "mal:10500": {"1": "1"}, "tvdb_show:259863:s1": {"1": "2"}},
  "anilist:10501": {"anidb:8257:R": {"1": "1"}, "imdb_movie:tt1866923": {"1": "1"}, "mal:10501": {"1": "1"}, "tmdb_movie:259485": {"1": "1"}, "tvdb_movie:53830": {"1": "1"}, "tvdb_show:259863:s1": {"1": "1"}},
  "anilist:10507": {"anidb:8381:R": {"1-47": "1-47"}, "mal:10507": {"1-47": "1-47"}, "tmdb_show:42912:s2": {"1-47": "1-47"}, "tvdb_show:146401:s2": {"1-47": "1-47"}}
}"""

# anilist_id -> (tvdb_series_id, season) -> (source_range) -> [(target_start, target_end, step, mode)]
# mode is None for anibridge (source-of-truth) mappings; only user overrides carry a MappingOverrideMode.
_EXPECTED_ANILIST_TVDB = {
    10471: {(261387, 0): {(1, 3): [(1, 3, 1, None)]}},
    10477: {(214891, 0): {(1, 1): [(10, 10, 1, None)]}},
    10490: {(249864, 1): {(1, 12): [(1, 12, 1, None)]}},
    10491: {(79682, 0): {(1, 4): [(2, 5, 1, None)]}},
    10495: {(250022, 1): {(1, 12): [(1, 12, 1, None)]}},
    10497: {(88161, 0): {(1, 4): [(5, 8, 1, None)]}},
    10500: {(259863, 1): {(1, 1): [(2, 2, 1, None)]}},
    10501: {(259863, 1): {(1, 1): [(1, 1, 1, None)]}},
    10507: {(146401, 2): {(1, 47): [(1, 47, 1, None)]}},
}


@dataclass
class Case:
    id: str
    source: bytes
    expected_result: tuple   # (anilist_tvdb, tvdb_anilist)


CASES = [
    Case(id="keeps only tvdb_show targets; reverse map empty without tvdb_show sources",
         source=_SOURCE, expected_result=(_EXPECTED_ANILIST_TVDB, {})),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__build_external_mappings(case: Case):
    assert AnimeRelations._build_external_mappings(case.source) == case.expected_result
