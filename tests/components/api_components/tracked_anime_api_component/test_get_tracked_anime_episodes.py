from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from common.exceptions import NotFoundException
from components.api_components.tracked_anime_api_component import TrackedAnimeAPIComponent
from api.schemas.tracked_anime_schemas import TrackedAnimeItemEpisode

_TA = "components.operational_components.tracked_anime_component.TrackedAnimeComponent"
_ANILIST = "components.service_components.anilist_component.AnilistComponent"
_COMPONENT = "components.api_components.tracked_anime_api_component.TrackedAnimeAPIComponent"


def make_episode_item(episode_number: int) -> TrackedAnimeItemEpisode:
    return TrackedAnimeItemEpisode(
        episode_number=episode_number, tvdb_series_episodes=[], tvdb_episode_part=None,
        tvdb_episode_part_ceiling=None, auto_discard=False, download_id=None, download_status=None)


@dataclass
class Case:
    id: str
    offset: int
    limit: int
    force_freshness: bool
    found: bool
    expected_lowest: int
    expected_highest: int


CASES = [
    Case(id="offset and limit map to episode window", offset=10, limit=25, force_freshness=False,
         found=True, expected_lowest=11, expected_highest=35),
    Case(id="first page from offset zero", offset=0, limit=5, force_freshness=True, found=True,
         expected_lowest=1, expected_highest=5),
    Case(id="missing tracked anime maps to NotFoundException", offset=0, limit=5,
         force_freshness=False, found=False, expected_lowest=0, expected_highest=0),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_tracked_anime_episodes(case: Case, make_anime, make_full_tracked_anime, mocker):
    component = TrackedAnimeAPIComponent()
    tracked = make_full_tracked_anime(anilist_id=8721)
    anime = make_anime(anilist_id=8721)
    episodes = [make_episode_item(case.expected_lowest), make_episode_item(case.expected_highest)]

    mocker.patch(f"{_TA}.get_tracked_anime_by_id", return_value=tracked if case.found else None)
    mocker.patch(f"{_ANILIST}.get_anime", return_value=anime)
    build = mocker.patch(f"{_COMPONENT}._build_episodes", new=AsyncMock(return_value=episodes))

    if not case.found:
        with pytest.raises(NotFoundException):
            await component.get_tracked_anime_episodes(tracked_anime_id=tracked.id, offset=case.offset,
                                                       limit=case.limit, force_freshness=case.force_freshness)
        build.assert_not_awaited()
        return

    result = await component.get_tracked_anime_episodes(tracked_anime_id=tracked.id, offset=case.offset,
                                                        limit=case.limit, force_freshness=case.force_freshness)

    assert result.episodes == episodes
    build.assert_awaited_once_with(tracked_anime=tracked, anime=anime, force_freshness=case.force_freshness,
                                   lowest=case.expected_lowest, highest=case.expected_highest)
