from dataclasses import dataclass

import pytest

from components.api_components.tracked_anime_api_component import TrackedAnimeAPIComponent

_TA = "components.operational_components.tracked_anime_component.TrackedAnimeComponent"


@dataclass
class Case:
    id: str


CASES = [
    Case(id="wraps the single id and forwards to operational unarchive"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_unarchive_tracked_anime(case: Case, mocker):
    unarchive = mocker.patch(f"{_TA}.unarchive_tracked_anime")

    await TrackedAnimeAPIComponent().unarchive_tracked_anime(tracked_anime_id=42)

    unarchive.assert_awaited_once_with(tracked_anime_ids=[42])
