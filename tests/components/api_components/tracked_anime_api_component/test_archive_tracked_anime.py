from dataclasses import dataclass

import pytest

from components.api_components.tracked_anime_api_component import TrackedAnimeAPIComponent

_TA = "components.operational_components.tracked_anime_component.TrackedAnimeComponent"


@dataclass
class Case:
    id: str


CASES = [
    Case(id="wraps the single id and forwards to operational archive"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_archive_tracked_anime(case: Case, mocker):
    archive = mocker.patch(f"{_TA}.archive_tracked_anime")

    await TrackedAnimeAPIComponent().archive_tracked_anime(tracked_anime_id=42)

    archive.assert_awaited_once_with(tracked_anime_ids=[42])
