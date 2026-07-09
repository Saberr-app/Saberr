from dataclasses import dataclass

import pytest

from components.api_components.user_anime_list_api_component import UserAnimeListAPIComponent
from dto.anilist import AnilistDate


@dataclass
class Case:
    id: str
    date: AnilistDate
    expected_result: tuple[int, int, int] | None


CASES = [
    Case(id="full date", date=AnilistDate(2021, 5, 3), expected_result=(2021, 5, 3)),
    Case(id="missing month and day default to zero", date=AnilistDate(2021, None, None),
         expected_result=(2021, 0, 0)),
    Case(id="missing year yields none", date=AnilistDate(None, None, None), expected_result=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__date_key(case: Case):
    assert UserAnimeListAPIComponent._date_key(case.date) == case.expected_result
