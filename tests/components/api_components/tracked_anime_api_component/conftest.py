from datetime import datetime
from itertools import count

import pytest

from config import config
from constants import (Encoding, Resolution, ReleaseCriteriaProperty, TrackedAnimeStatus, TVDBSeasonType,
                       VideoSource)
from dto.anilist import AnilistAnime, AnilistDate, AnilistAnimeStatus
from dto.orm_models import (TrackedAnime, TrackedAnimeProfile, TrackedAnimeProcessingSettings,
                            TrackedAnimeReleaseGroupPreferences)
from dto.tvdb import TVDBSeriesEpisodes, TVDBSeriesEpisode

_ids = count(1)


@pytest.fixture
def make_anime():
    def _make(anilist_id, episodes=12, next_airing_episode=None):
        return AnilistAnime(
            id=anilist_id, idMal=None, english_title="English", romaji_title="Romaji",
            native_title="ネイティブ", description=None, season=None, season_year=None, episodes=episodes,
            duration=None, source=None, status=AnilistAnimeStatus.FINISHED, average_score=None,
            mean_score=None, popularity=None, format=None, country_of_origin=None, hashtag=None,
            synonyms=[], start_date=AnilistDate(None, None, None), end_date=AnilistDate(None, None, None),
            genres=[], tags=[], is_adult=False, next_airing_episode=next_airing_episode, studios=[],
            trailer_url=None, banner_image=None, small_cover_image=None, medium_cover_image=None,
            large_cover_image=None, external_links=[],
        )
    return _make


@pytest.fixture
def make_full_tracked_anime():
    """Build a fully-wired in-memory TrackedAnime graph (profile + processing settings + a preference
    per configured release group + empty episodes) so TrackedAnimeAPIComponent._to_item can map it
    without a DB."""
    def _make(*, anilist_id=1, tvdb_structure_enabled=False, tvdb_season_type=TVDBSeasonType.OFFICIAL,
              show_folder_name="Show", episode_number_padding=2):
        profile = TrackedAnimeProfile(
            preferred_release_groups=["SubsPlease"], preferred_encodings=[Encoding.HEVC],
            preferred_resolutions=[Resolution.P1080], preferred_language_codes=["JP"],
            preferred_sources=[VideoSource.CRUNCHYROLL], language_codes_restricted=False,
            sources_restricted=False, accept_release_upgrades=True,
            priorities_sorted=[ReleaseCriteriaProperty.RESOLUTION])
        profile.id = 1

        processing = TrackedAnimeProcessingSettings(
            episode_number_padding=episode_number_padding, season_number_padding=2,
            season_directory_number_padding=1, season_directory_name_format="Season {season_number}",
            raw_episode_file_name_format="{episode_number}", episode_file_name_format="{episode_title}",
            titleless_episode_file_name_format="{episode_number}")

        tracked = TrackedAnime(
            romaji_title="Romaji", native_title="ネイティブ", english_title="English", anilist_id=anilist_id,
            status=TrackedAnimeStatus.ACTIVE, tvdb_structure_enabled=tvdb_structure_enabled, from_episode=1,
            tvdb_season_type=tvdb_season_type, show_parent_directory="/anime",
            show_folder_name=show_folder_name)
        tracked.id = next(_ids)
        tracked.tracked_anime_profile_id = 1
        tracked.profile = profile
        tracked.processing_settings = processing
        tracked.release_groups_preferences = [
            TrackedAnimeReleaseGroupPreferences(
                tracked_anime_id=tracked.id, release_group=rg_name,
                episode_number_offset=0, override_match_against=None)
            for rg_name, _ in config.release_groups_map.items()
        ]
        tracked.episodes = []
        return tracked
    return _make


@pytest.fixture
def make_tvdb_episodes():
    def _make(series_id=55, season_number=1, count_=12):
        episodes = [
            TVDBSeriesEpisode(id=1000 + n, series_id=series_id, title=f"E{n}",
                              air_date=datetime(2020, 1, n), runtime=24, overview=None, image_url=None,
                              number=n, absolute_number=n, season_number=season_number, season_name="S1",
                              finale_type=None, season_type=TVDBSeasonType.OFFICIAL)
            for n in range(1, count_ + 1)
        ]
        return TVDBSeriesEpisodes(series_id=series_id, season_type=TVDBSeasonType.OFFICIAL,
                                  episodes=episodes)
    return _make
