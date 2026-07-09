from dataclasses import dataclass

import pytest

from components.api_components.user_anime_list_api_component import UserAnimeListAPIComponent
from api.schemas.user_anime_list_schemas import UserAnimeListRequest
from constants import SortDirection
from tests.support.builders import make_anime, make_entry

_SortBy = UserAnimeListRequest.UserAnimeListSortBy

# three entries with episode counts 5, 12 and one missing (None)
_PAIRS = [
    (make_entry(1), make_anime(1, title="A", episodes=5)),
    (make_entry(2), make_anime(2, title="B", episodes=12)),
    (make_entry(3), make_anime(3, title="C", episodes=None)),
]


def _component():
    return UserAnimeListAPIComponent.__new__(UserAnimeListAPIComponent)


@dataclass
class Case:
    id: str
    direction: SortDirection
    expected_ids: list[int]


CASES = [
    # missing sort values always sort last, regardless of direction
    Case(id="ascending by episodes, missing last", direction=SortDirection.ASC, expected_ids=[1, 2, 3]),
    Case(id="descending by episodes, missing last", direction=SortDirection.DESC, expected_ids=[2, 1, 3]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__sort(case: Case):
    result = _component()._sort(_PAIRS, _SortBy.EPISODES, case.direction)
    assert [anime.id for _entry, anime in result] == case.expected_ids
