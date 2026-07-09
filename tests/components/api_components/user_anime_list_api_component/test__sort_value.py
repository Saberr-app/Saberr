from dataclasses import dataclass
from typing import Callable

import pytest

from components.api_components.user_anime_list_api_component import UserAnimeListAPIComponent
from api.schemas.user_anime_list_schemas import UserAnimeListRequest
from tests.support.builders import make_anime, make_entry

_SortBy = UserAnimeListRequest.UserAnimeListSortBy


def _component():
    return UserAnimeListAPIComponent.__new__(UserAnimeListAPIComponent)


@dataclass
class Case:
    id: str
    sort_by: object
    build: Callable               # () -> (entry, anime)
    expected_result: object


CASES = [
    Case(id="title uses the configured title key", sort_by=_SortBy.TITLE,
         build=lambda: (make_entry(1), make_anime(1, title="Some Title")), expected_result="Some Title"),
    Case(id="episodes", sort_by=_SortBy.EPISODES,
         build=lambda: (make_entry(1), make_anime(1, episodes=12)), expected_result=12),
    Case(id="progress", sort_by=_SortBy.PROGRESS,
         build=lambda: (make_entry(1, progress=7), make_anime(1)), expected_result=7),
    Case(id="score", sort_by=_SortBy.SCORE,
         build=lambda: (make_entry(1, score=8.5), make_anime(1)), expected_result=8.5),
    Case(id="status uses the enum value", sort_by=_SortBy.STATUS,
         build=lambda: (make_entry(1, status="CURRENT"), make_anime(1)), expected_result="CURRENT"),
    Case(id="started at uses the date key", sort_by=_SortBy.STARTED_AT,
         build=lambda: (make_entry(1, started_at=(2021, 5, 3)), make_anime(1)),
         expected_result=(2021, 5, 3)),
    Case(id="season and year combine year with a season rank", sort_by=_SortBy.SEASON_AND_YEAR,
         build=lambda: (make_entry(1), make_anime(1, season="SUMMER", season_year=2024)),
         expected_result=(2024, 2)),
    Case(id="season and year missing year yields none", sort_by=_SortBy.SEASON_AND_YEAR,
         build=lambda: (make_entry(1), make_anime(1, season="SUMMER")), expected_result=None),
    Case(id="time until airing none without a schedule", sort_by=_SortBy.TIME_UNTIL_AIRING,
         build=lambda: (make_entry(1), make_anime(1)), expected_result=None),
    Case(id="time until airing uses the next airing timestamp", sort_by=_SortBy.TIME_UNTIL_AIRING,
         build=lambda: (make_entry(1), make_anime(1, airing_at=1700)), expected_result=1700),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__sort_value(case: Case):
    entry, anime = case.build()
    assert _component()._sort_value(entry, anime, case.sort_by) == case.expected_result
