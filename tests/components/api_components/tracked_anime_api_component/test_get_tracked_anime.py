from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from components.api_components.tracked_anime_api_component import TrackedAnimeAPIComponent
from dto.tvdb import AnilistEpisodeTVDBMapping

_TA = "components.operational_components.tracked_anime_component.TrackedAnimeComponent"
_ANILIST = "components.service_components.anilist_component.AnilistComponent"
_AIRING = ("components.service_components.anilist_airing_schedule_component"
           ".AnilistAiringScheduleComponent")
_TVDB = "components.service_components.tvdb_component.TVDBComponent"
_MODULE = "components.api_components.tracked_anime_api_component"


@dataclass
class Case:
    id: str
    anilist_id: int
    episodes: int
    series_id: int
    tvdb_count: int
    expected_episode_numbers: list[int]
    expected_first_tvdb_id: int


CASES = [
    # finished, no next airing -> latest=12; highest=min(15,12)=12
    Case(id="builds episode window and tvdb", anilist_id=8521, episodes=12, series_id=55,
         tvdb_count=12, expected_episode_numbers=list(range(1, 13)), expected_first_tvdb_id=1001),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_tracked_anime(case: Case, make_anime, make_full_tracked_anime, make_tvdb_episodes,
                                 mocker):
    anime = make_anime(anilist_id=case.anilist_id, episodes=case.episodes)
    tracked = make_full_tracked_anime(anilist_id=case.anilist_id)

    async def fake_mappings(anilist_id, episode_number):
        return [AnilistEpisodeTVDBMapping(series_id=case.series_id, season_number=1,
                                          episode_number=episode_number, part=None, part_ceiling=None)]

    mocker.patch(f"{_TA}.get_tracked_anime_by_id", return_value=tracked)
    mocker.patch(f"{_ANILIST}.get_anime", return_value=anime)
    mocker.patch(f"{_AIRING}.get_future_anime_schedule_records_map", return_value={})
    mocker.patch(f"{_TVDB}.get_series_episodes",
                 return_value=make_tvdb_episodes(series_id=case.series_id, count_=case.tvdb_count))
    mocker.patch(f"{_MODULE}.anime_relations.get_anilist_episode_tvdb_mappings",
                 new=AsyncMock(side_effect=fake_mappings))
    mocker.patch(f"{_MODULE}.anime_relations.get_anilist_id_tvdb_series_id", return_value=case.series_id)

    result = await TrackedAnimeAPIComponent().get_tracked_anime(tracked_anime_id=tracked.id)

    assert [ep.episode_number for ep in result.episodes] == case.expected_episode_numbers
    assert result.episodes[0].tvdb_series_episodes[0].id == case.expected_first_tvdb_id
    assert result.episodes[0].download_id is None
    assert result.episodes[0].auto_discard is False
