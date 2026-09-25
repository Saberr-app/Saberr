import copy
import json
import logging
from dataclasses import dataclass, field

import pytest

from constants import MappingOverrideMode

ALWAYS = MappingOverrideMode.ALWAYS


def row(tvdb_series=5000, tvdb_season=1, anilist_from=1, anilist_to=12, tvdb_from=1, tvdb_to=12, gran=1):
    return dict(tvdb_series=tvdb_series, tvdb_season=tvdb_season, anilist_from=anilist_from, anilist_to=anilist_to,
                tvdb_from=tvdb_from, tvdb_to=tvdb_to, gran=gran)


def hot(mappings) -> bytes:
    return json.dumps({"$meta": {"schema_version": "1.0"}, "mappings": mappings}).encode()


@dataclass
class Case:
    id: str
    overrides_data: bytes
    expected_result: tuple   # (anilist_tvdb, tvdb_anilist) after the in-place update
    anilist_tvdb: dict = field(default_factory=dict)
    tvdb_anilist: dict = field(default_factory=dict)


CASES = [
    Case(id="row is added in both directions tagged ALWAYS",
         overrides_data=hot({"100": [row()]}),
         expected_result=(
             {100: {(5000, 1): {(1, 12): [(1, 12, 1, ALWAYS)]}}},
             {(5000, 1): {100: {(1, 12): [(1, 12, 1, ALWAYS)]}}},
         )),
    Case(id="open-ended row keeps open ends",
         overrides_data=hot({"100": [row(tvdb_season=2, anilist_to=None, tvdb_to=None)]}),
         expected_result=(
             {100: {(5000, 2): {(1, None): [(1, None, 1, ALWAYS)]}}},
             {(5000, 2): {100: {(1, None): [(1, None, 1, ALWAYS)]}}},
         )),
    # gran is authored anilist -> tvdb; the reverse direction gets its sign flipped when |gran| >= 2
    Case(id="gran is flipped for the tvdb -> anilist direction",
         overrides_data=hot({"100": [row(tvdb_to=6, gran=2)]}),
         expected_result=(
             {100: {(5000, 1): {(1, 12): [(1, 6, 2, ALWAYS)]}}},
             {(5000, 1): {100: {(1, 6): [(1, 12, -2, ALWAYS)]}}},
         )),
    Case(id="anibridge entries of the same anime are kept alongside",
         anilist_tvdb={100: {(9000, 1): {(1, 12): [(1, 12, 1, None)]}}},
         tvdb_anilist={(9000, 1): {100: {(1, 12): [(1, 12, 1, None)]}}},
         overrides_data=hot({"100": [row()]}),
         expected_result=(
             {100: {(9000, 1): {(1, 12): [(1, 12, 1, None)]},
                    (5000, 1): {(1, 12): [(1, 12, 1, ALWAYS)]}}},
             {(9000, 1): {100: {(1, 12): [(1, 12, 1, None)]}},
              (5000, 1): {100: {(1, 12): [(1, 12, 1, ALWAYS)]}}},
         )),
    Case(id="identical anibridge range gets the hot target appended next to it",
         anilist_tvdb={100: {(5000, 1): {(1, 12): [(1, 12, 1, None)]}}},
         tvdb_anilist={(5000, 1): {100: {(1, 12): [(1, 12, 1, None)]}}},
         overrides_data=hot({"100": [row()]}),
         expected_result=(
             {100: {(5000, 1): {(1, 12): [(1, 12, 1, None), (1, 12, 1, ALWAYS)]}}},
             {(5000, 1): {100: {(1, 12): [(1, 12, 1, None), (1, 12, 1, ALWAYS)]}}},
         )),
    Case(id="other anime are left untouched",
         anilist_tvdb={200: {(7000, 1): {(1, 12): [(1, 12, 1, None)]}}},
         overrides_data=hot({"100": [row()]}),
         expected_result=(
             {200: {(7000, 1): {(1, 12): [(1, 12, 1, None)]}},
              100: {(5000, 1): {(1, 12): [(1, 12, 1, ALWAYS)]}}},
             {(5000, 1): {100: {(1, 12): [(1, 12, 1, ALWAYS)]}}},
         )),
    Case(id="season separator keys are skipped",
         overrides_data=hot({"$season-separator:fall-2026": None, "100": [row()]}),
         expected_result=(
             {100: {(5000, 1): {(1, 12): [(1, 12, 1, ALWAYS)]}}},
             {(5000, 1): {100: {(1, 12): [(1, 12, 1, ALWAYS)]}}},
         )),
    # one bad row skips the whole anime so it is never half-overridden; the anibridge mapping stays
    Case(id="anime with a malformed row is skipped entirely",
         anilist_tvdb={100: {(9000, 1): {(1, 12): [(1, 12, 1, None)]}}},
         overrides_data=hot({"100": [row(), {"tvdb_series": 5000}], "200": [row(tvdb_series=6000)]}),
         expected_result=(
             {100: {(9000, 1): {(1, 12): [(1, 12, 1, None)]}},
              200: {(6000, 1): {(1, 12): [(1, 12, 1, ALWAYS)]}}},
             {(6000, 1): {200: {(1, 12): [(1, 12, 1, ALWAYS)]}}},
         )),
    Case(id="anime with an invalid gran is skipped",
         overrides_data=hot({"100": [row(gran=-1)]}),
         expected_result=({}, {})),
    Case(id="unparseable data leaves the maps untouched",
         anilist_tvdb={100: {(9000, 1): {(1, 12): [(1, 12, 1, None)]}}},
         overrides_data=b"not json",
         expected_result=({100: {(9000, 1): {(1, 12): [(1, 12, 1, None)]}}}, {})),
    Case(id="non-object top level leaves the maps untouched",
         anilist_tvdb={100: {(9000, 1): {(1, 12): [(1, 12, 1, None)]}}},
         overrides_data=b"[]",
         expected_result=({100: {(9000, 1): {(1, 12): [(1, 12, 1, None)]}}}, {})),
    Case(id="non-object mappings leaves the maps untouched",
         anilist_tvdb={100: {(9000, 1): {(1, 12): [(1, 12, 1, None)]}}},
         overrides_data=b'{"mappings": [1]}',
         expected_result=({100: {(9000, 1): {(1, 12): [(1, 12, 1, None)]}}}, {})),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__override_external_mappings(case: Case, make_relations):
    ar = make_relations()
    ar.logger = logging.getLogger("test")
    anilist_tvdb, tvdb_anilist = copy.deepcopy(case.anilist_tvdb), copy.deepcopy(case.tvdb_anilist)
    ar._override_external_mappings(anilist_tvdb, tvdb_anilist, case.overrides_data)
    assert (anilist_tvdb, tvdb_anilist) == case.expected_result
