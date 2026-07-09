from dataclasses import dataclass, field

import pytest

from components.api_components.user_anime_list_api_component import UserAnimeListAPIComponent
from api.schemas.user_anime_list_schemas import UserAnimeListRequest
from constants import AnilistAnimeSeason, AnilistAnimeUserStatus
from tests.support.builders import make_anime, make_entry

# id1: Naruto, currently watching, summer 2024, tracked; id2: Bleach, completed, winter 2020, untracked
_PAIRS = [
    (make_entry(1, status="CURRENT"),
     make_anime(1, title="Naruto", season="SUMMER", season_year=2024, synonyms=["NRT"])),
    (make_entry(2, status="COMPLETED"),
     make_anime(2, title="Bleach", season="WINTER", season_year=2020)),
]
_TRACKED_MAP = {1: 10}  # id1 is tracked, id2 is not


@dataclass
class Case:
    id: str
    params: dict = field(default_factory=dict)
    expected_ids: list[int] = field(default_factory=lambda: [1, 2])


CASES = [
    Case(id="no filters keeps everything", expected_ids=[1, 2]),
    Case(id="query matches a title", params=dict(query="naru"), expected_ids=[1]),
    Case(id="query matches a synonym", params=dict(query="nrt"), expected_ids=[1]),
    Case(id="status filter", params=dict(statuses=[AnilistAnimeUserStatus.COMPLETED]), expected_ids=[2]),
    Case(id="season filter", params=dict(season=AnilistAnimeSeason.SUMMER), expected_ids=[1]),
    Case(id="season year filter", params=dict(season_year=2020), expected_ids=[2]),
    Case(id="only tracked", params=dict(is_tracked=True), expected_ids=[1]),
    Case(id="only untracked", params=dict(is_tracked=False), expected_ids=[2]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__filter(case: Case):
    params = UserAnimeListRequest(**case.params)
    result = UserAnimeListAPIComponent._filter(_PAIRS, params, _TRACKED_MAP)
    assert [anime.id for _entry, anime in result] == case.expected_ids
