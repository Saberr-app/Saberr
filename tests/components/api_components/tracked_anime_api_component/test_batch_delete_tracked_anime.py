from dataclasses import dataclass

import pytest

from components.api_components.tracked_anime_api_component import TrackedAnimeAPIComponent
from api.schemas.tracked_anime_schemas import TrackedAnimeBatchDeleteRequest

_TA = "components.operational_components.tracked_anime_component.TrackedAnimeComponent"


@dataclass
class Case:
    id: str
    anilist_ids: list[int]


CASES = [
    Case(id="forwards the requested anilist ids to operational delete", anilist_ids=[4, 5]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_batch_delete_tracked_anime(case: Case, mocker):
    delete = mocker.patch(f"{_TA}.delete_tracked_anime")

    await TrackedAnimeAPIComponent().batch_delete_tracked_anime(
        body=TrackedAnimeBatchDeleteRequest(anilist_ids=case.anilist_ids))

    delete.assert_awaited_once_with(anilist_ids=case.anilist_ids)
