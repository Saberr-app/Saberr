from dataclasses import dataclass

import pytest

from constants import (TVDBSeasonType, Encoding, Resolution, VideoSource, ReleaseCriteriaProperty)
from dto.anilist import AnilistAnime, AnilistDate, AnilistAnimeStatus


@dataclass
class SimpleProfile:
    preferred_release_groups: list
    preferred_encodings: list
    preferred_resolutions: list
    preferred_language_codes: list
    preferred_sources: list
    language_codes_restricted: bool
    sources_restricted: bool
    accept_release_upgrades: bool
    priorities_sorted: list


@pytest.fixture
def make_anime():
    def _make(anilist_id, romaji="Romaji", native="ネイティブ", english="English", episodes=12):
        return AnilistAnime(
            id=anilist_id, idMal=None, english_title=english, romaji_title=romaji, native_title=native,
            description=None, season=None, season_year=None, episodes=episodes, duration=None, source=None,
            status=AnilistAnimeStatus.FINISHED, average_score=None, mean_score=None, popularity=None,
            format=None, country_of_origin=None, hashtag=None, synonyms=[],
            start_date=AnilistDate(None, None, None), end_date=AnilistDate(None, None, None),
            genres=[], tags=[], is_adult=False, next_airing_episode=None, studios=[], trailer_url=None,
            banner_image=None, small_cover_image=None, medium_cover_image=None, large_cover_image=None,
            external_links=[],
        )
    return _make


@pytest.fixture
def base_kwargs():
    def _make(anilist_anime, **overrides):
        kwargs = dict(
            anilist_anime=anilist_anime,
            from_episode=1,
            tvdb_structure_enabled=False,
            tvdb_season_type=TVDBSeasonType.OFFICIAL,
            show_parent_directory="/anime",
            show_folder_name="Show",
            episode_number_padding=2,
            season_number_padding=2,
            season_directory_number_padding=1,
            season_directory_name_format="Season {season}",
            raw_episode_file_name_format="{title} - {episode}",
            episode_file_name_format="{title} - {episode}",
            titleless_episode_file_name_format="{episode}",
            release_group_overriding_title_map={},
            release_group_overriding_offset_map={},
            release_profile=None,
        )
        kwargs.update(overrides)
        return kwargs
    return _make


@pytest.fixture
def fresh_tracked():
    """Read a tracked anime through a brand-new session each call.

    The component write methods commit via their own `require_db_session` session/connection, so a
    reader that began its transaction earlier won't see those commits (SQLite snapshot). A fresh
    session per read always observes the latest committed state.
    """
    import common.db as db
    from repositories.tracked_anime_repositories.tracked_anime_repo import TrackedAnimeRepo

    async def _read(*, tracked_anime_id=None, anilist_id=None, load_relations=True):
        async with db.AsyncSessionLocal() as s:
            return await TrackedAnimeRepo(s).get_tracked_anime(
                tracked_anime_id=tracked_anime_id, anilist_id=anilist_id, load_relations=load_relations
            )
    return _read


@pytest.fixture
def fresh_profile():
    import common.db as db
    from repositories.tracked_anime_repositories.tracked_anime_profile_repo import TrackedAnimeProfileRepo

    async def _read(profile_id):
        async with db.AsyncSessionLocal() as s:
            return await TrackedAnimeProfileRepo(s).get_tracked_anime_profile(
                tracked_anime_profile_id=profile_id
            )
    return _read


@pytest.fixture
def profile_settings():
    return SimpleProfile(
        preferred_release_groups=[],
        preferred_encodings=[Encoding.HEVC],
        preferred_resolutions=[Resolution.P1080],
        preferred_language_codes=["eng"],
        preferred_sources=[VideoSource.CRUNCHYROLL],
        language_codes_restricted=True,
        sources_restricted=True,
        accept_release_upgrades=False,
        priorities_sorted=[ReleaseCriteriaProperty.RESOLUTION],
    )
