from dataclasses import dataclass, field
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app_state import anime_relations
from components.api_components.tracked_anime_api_component import TrackedAnimeAPIComponent
from constants import TVDBSeasonType
from dto.anilist import AnilistAiringScheduleItem
from dto.tvdb import AnilistEpisodeTVDBMapping, TVDBEpisodeAnilistMapping, TVDBSeriesEpisode

_PAST = datetime(2000, 1, 1)    # always already aired
_FUTURE = datetime(2999, 1, 1)  # never aired yet


def _tvdb_ep(ep_id: int, number: int, season_number: int, air_date) -> TVDBSeriesEpisode:
    return TVDBSeriesEpisode(
        id=ep_id, series_id=55, title=f"E{number}", air_date=air_date, runtime=24, overview=None,
        image_url=None, number=number, absolute_number=number, season_number=season_number,
        season_name="S", finale_type=None, season_type=TVDBSeasonType.OFFICIAL,
    )


def _mapping(season_number: int) -> AnilistEpisodeTVDBMapping:
    return AnilistEpisodeTVDBMapping(series_id=55, season_number=season_number, episode_number=1, part=None)


@dataclass
class Case:
    id: str
    expected_result: int
    next_airing_episode: int | None = None
    episodes: int | None = None
    anilist_tvdb_mappings: list = field(default_factory=list)
    tvdb_episodes: list | None = field(default_factory=list)  # None => the tvdb_episodes callable raises


CASES = [
    # tier 1: next airing episode wins, even when episodes is set; latest aired = next - 1
    Case(id="next-airing-minus-one", next_airing_episode=5, episodes=12, expected_result=4),
    # tier 1: floor at 1 when nothing has aired yet (next episode is 1)
    Case(id="next-airing-one-floors-to-1", next_airing_episode=1, episodes=12, expected_result=1),
    # tier 2: no next airing -> total episode count
    Case(id="no-next-airing-uses-episode-count", episodes=12, expected_result=12),
    # tier 3 entry guards -> floor of 1
    Case(id="no-mappings-returns-1", anilist_tvdb_mappings=[], expected_result=1),
    Case(id="tvdb-fetch-fails-returns-1", anilist_tvdb_mappings=[_mapping(1)], tvdb_episodes=None,
         expected_result=1),
    # tier 3 success: max aired episode in the mapped season; future ep and season-0 special excluded
    Case(id="fallback-max-aired-in-season", anilist_tvdb_mappings=[_mapping(1)],
         tvdb_episodes=[_tvdb_ep(1, 1, 1, _PAST), _tvdb_ep(2, 2, 1, _PAST), _tvdb_ep(3, 3, 1, _PAST),
                        _tvdb_ep(4, 4, 1, _FUTURE), _tvdb_ep(5, 99, 0, _PAST)],
         expected_result=3),
    # tier 3 quirk: season 0 mapping is filtered out by `season != 0`, so it floors to 1
    Case(id="fallback-season-zero-returns-1", anilist_tvdb_mappings=[_mapping(0)],
         tvdb_episodes=[_tvdb_ep(1, 1, 0, _PAST), _tvdb_ep(2, 2, 0, _PAST)],
         expected_result=1),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_determine_latest_episode(case, mocker, make_anime):
    component = TrackedAnimeAPIComponent.__new__(TrackedAnimeAPIComponent)
    anime = make_anime(
        anilist_id=1, episodes=case.episodes,
        next_airing_episode=AnilistAiringScheduleItem(anilist_id=1, episode=case.next_airing_episode, airing_at=None)
        if case.next_airing_episode is not None else None,
    )

    mocker.patch.object(anime_relations, "get_anilist_episode_tvdb_mappings",
                        new=AsyncMock(return_value=case.anilist_tvdb_mappings))
    # identity reverse-mapping: a TVDB episode number maps to the same AniList episode number
    mocker.patch.object(anime_relations, "get_tvdb_episode_anilist_mappings",
                        new=AsyncMock(side_effect=lambda series_id, season_number, episode_number: [
                            TVDBEpisodeAnilistMapping(anilist_id=anime.id, episode_number=episode_number, part=None)
                        ]))

    async def tvdb_episodes(series_id, season_type):
        if case.tvdb_episodes is None:
            raise RuntimeError("tvdb unavailable")
        return {ep.id: ep for ep in case.tvdb_episodes}

    result = await component._determine_latest_episode(anime, tvdb_episodes)

    assert result == case.expected_result
