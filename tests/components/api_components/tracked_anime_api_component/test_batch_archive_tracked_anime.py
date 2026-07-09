from dataclasses import dataclass

import pytest

from components.api_components.tracked_anime_api_component import TrackedAnimeAPIComponent
from api.schemas.tracked_anime_schemas import TrackedAnimeBatchArchiveRequest

_TA = "components.operational_components.tracked_anime_component.TrackedAnimeComponent"


@dataclass
class Case:
    id: str
    anilist_ids: list[int]


CASES = [
    Case(id="forwards the requested anilist ids to operational archive", anilist_ids=[1, 2, 3]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_batch_archive_tracked_anime(case: Case, mocker):
    archive = mocker.patch(f"{_TA}.archive_tracked_anime")

    await TrackedAnimeAPIComponent().batch_archive_tracked_anime(
        body=TrackedAnimeBatchArchiveRequest(anilist_ids=case.anilist_ids))

    archive.assert_awaited_once_with(anilist_ids=case.anilist_ids)
