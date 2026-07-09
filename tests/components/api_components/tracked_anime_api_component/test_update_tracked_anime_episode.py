from dataclasses import dataclass

import pytest

from components.api_components.tracked_anime_api_component import TrackedAnimeAPIComponent
from api.schemas.tracked_anime_schemas import TrackedAnimeEpisodeUpdateRequest

_EPISODE = ("components.operational_components.tracked_anime_episode_component"
            ".TrackedAnimeEpisodeComponent.update_tracked_anime_episode")


@dataclass
class Case:
    id: str
    tracked_anime_id: int
    episode_number: int
    auto_discard: bool


CASES = [
    Case(id="forwards auto_discard true", tracked_anime_id=5, episode_number=3, auto_discard=True),
    Case(id="forwards auto_discard false", tracked_anime_id=6, episode_number=12, auto_discard=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_tracked_anime_episode(case: Case, mocker):
    op_update = mocker.patch(_EPISODE)

    await TrackedAnimeAPIComponent().update_tracked_anime_episode(
        tracked_anime_id=case.tracked_anime_id, episode_number=case.episode_number,
        data=TrackedAnimeEpisodeUpdateRequest(auto_discard=case.auto_discard))

    op_update.assert_awaited_once_with(tracked_anime_id=case.tracked_anime_id,
                                       episode_number=case.episode_number,
                                       auto_discard=case.auto_discard)
