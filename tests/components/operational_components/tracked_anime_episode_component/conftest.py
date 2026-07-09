import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from dto.tvdb import AnilistEpisodeTVDBMapping


@pytest.fixture
def make_component():
    """A TrackedAnimeEpisodeComponent without its heavy __init__; sub-components are mocks.

    The component's logic talks to repos (patched per test at class level) and `app_state.anime_relations`,
    so only `_tvdb_component` needs to be a stand-in for the TVDB lookups it performs directly.
    """
    from components.operational_components.tracked_anime_episode_component import TrackedAnimeEpisodeComponent

    def _make():
        component = TrackedAnimeEpisodeComponent.__new__(TrackedAnimeEpisodeComponent)
        component.logger = logging.getLogger("test.tracked_anime_episode_component")
        component._tvdb_component = MagicMock()
        component._tvdb_component.get_series_episodes = AsyncMock()
        component._tracked_anime_component = MagicMock()
        return component
    return _make


@pytest.fixture
def make_mapping():
    def _make(*, series_id=100, season_number=1, episode_number=1, part=None, part_ceiling=None,
              episode_id=None):
        return AnilistEpisodeTVDBMapping(series_id=series_id, season_number=season_number,
                                         episode_number=episode_number, part=part,
                                         part_ceiling=part_ceiling, episode_id=episode_id)
    return _make


@pytest.fixture
def make_tvdb_episodes():
    """Mimic TVDBSeriesEpisodes: an object exposing `.episodes`, each with season_number/number/id."""
    def _make(episodes: list[tuple[int, int, int]]):
        return SimpleNamespace(episodes=[
            SimpleNamespace(season_number=season, number=number, id=episode_id)
            for season, number, episode_id in episodes
        ])
    return _make
