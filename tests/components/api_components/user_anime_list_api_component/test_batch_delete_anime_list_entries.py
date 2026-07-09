from dataclasses import dataclass

import pytest

from components.api_components.user_anime_list_api_component import UserAnimeListAPIComponent
from api.schemas.user_anime_list_schemas import UserAnimeBatchDeleteRequest

_LIST = "components.service_components.anilist_list_component.AnilistListComponent"


@dataclass
class Case:
    id: str
    anilist_ids: list[int]


CASES = [
    Case(id="forwards the requested anilist ids to the list service", anilist_ids=[1, 2, 3]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_batch_delete_anime_list_entries(case: Case, mocker):
    delete = mocker.patch(f"{_LIST}.delete_user_list_entries")

    await UserAnimeListAPIComponent().batch_delete_anime_list_entries(
        body=UserAnimeBatchDeleteRequest(anilist_ids=case.anilist_ids))

    delete.assert_awaited_once_with(anilist_ids=case.anilist_ids)
