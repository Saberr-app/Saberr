"""Real domain-object builders shared across test files. Prefer these over per-directory factories.

Each builder returns a real DTO/value object with sensible defaults; tests override only the fields
they exercise.
"""
from constants import ExternalServiceCode, AnilistTitleLanguage, RSSCategory, MappingOverrideMode
from dto.anilist import AnilistAiringScheduleItem, AnilistAnime, AnilistUserList, AnilistUserListEntry
from dto.orm_models import MappingOverride
from dto.settings import UserSettings
from dto.tvdb import TVDBSeries
from workers.downstream_healthcheck_workers import ServiceStatus

# Default user settings, mirroring the DB seed (scripts/sql/latest_schema.sql). Tests get these via the
# autouse `user_settings` fixture in the root conftest; override individual fields per case.
_DEFAULT_USER_SETTINGS = dict(
    anilist_username=None,
    anilist_user_token=None,
    anilist_user_data=None,
    qbit_base_url=None,
    qbit_username=None,
    qbit_password=None,
    qbit_remote_path_mapping=None,
    default_destination_directory=None,
    default_show_directory_name_format="{tvdb_title_english}",
    default_season_directory_name_format="Season {season_number}",
    default_raw_episode_file_name_format="{anilist_title_romaji} - {episode_number}",
    default_episode_file_name_format="{tvdb_title_english} - S{season_number}E{episode_number} - {episode_title}",
    default_titleless_episode_file_name_format="{tvdb_title_english} - S{season_number}E{episode_number}",
    tvdb_structure_enabled_default=True,
    torrent_category="Seasonal Anime",
    staging_directory=None,
    organize_downloads=True,
    apply_release_group_as_torrent_tag=True,
    apply_encoding_as_torrent_tag=False,
    apply_resolution_as_torrent_tag=False,
    apply_language_code_as_torrent_tag=False,
    apply_anime_title_as_torrent_tag=True,
    auto_download=True,
    rss_check_frequency=600,
    rss_category=RSSCategory.ENGLISH_TRANSLATED,
    set_download_as_failed_after_minutes=180,
    set_processing_as_failed_after_minutes=15,
    notifications_discord_webhook_url=None,
    discord_webhook_username=None,
    discord_webhook_avatar_url=None,
    discord_notify_on_login=False,
    discord_notify_on_download_processed=True,
    discord_notify_on_upgrade_download_processed=False,
    discord_notify_on_download_failed=True,
    discord_user_id=None,
    timezone="UTC",
    anilist_preferred_title_language=AnilistTitleLanguage.ROMAJI,
    published_url=None,
)


def make_user_settings(**overrides) -> UserSettings:
    return UserSettings(**{**_DEFAULT_USER_SETTINGS, **overrides})


def make_anime(anime_id: int,
               title: str = "Title",
               season_year: int | None = None,
               season: str | None = None,
               episodes: int | None = None,
               anime_format: str | None = None,
               source: str | None = None,
               status: str = "FINISHED",
               synonyms: list[str] | None = None,
               airing_at: int | None = None) -> AnilistAnime:
    # english/romaji/native kept identical so sorting is independent of configured title language.
    data = {
        "id": anime_id,
        "title": {"english": title, "romaji": title, "native": title},
        "season": season,
        "seasonYear": season_year,
        "episodes": episodes,
        "format": anime_format,
        "source": source,
        "status": status,
        "synonyms": synonyms or [],
    }
    if airing_at is not None:
        data["nextAiringEpisode"] = {"airingAt": airing_at, "episode": 1}
    return AnilistAnime.from_dict(data)


def make_entry(anime_id: int,
               status: str = "COMPLETED",
               score: float = 0.0,
               progress: int = 0,
               repeat_count: int = 0,
               is_private: bool = False,
               started_at: tuple[int, int, int] | None = None,
               completed_at: tuple[int, int, int] | None = None,
               notes: str | None = None) -> AnilistUserListEntry:
    def _date(d):
        if d is None:
            return None
        year, month, day = d
        return {"year": year, "month": month, "day": day}

    return AnilistUserListEntry.from_dict({
        "id": anime_id * 1000,
        "mediaId": anime_id,
        "status": status,
        "score": score,
        "progress": progress,
        "repeat": repeat_count,
        "private": is_private,
        "startedAt": _date(started_at),
        "completedAt": _date(completed_at),
        "notes": notes,
    })


def make_user_list(entries: list[AnilistUserListEntry]) -> AnilistUserList:
    return AnilistUserList.from_list_of_dict([entry.raw_data for entry in entries])


def make_airing(airing_at: int, episode: int, anilist_id: int) -> AnilistAiringScheduleItem:
    return AnilistAiringScheduleItem(airing_at=airing_at, episode=episode, anilist_id=anilist_id)


# A valid 1:1 mapping override (anilist eps 1-3 -> tvdb S1 eps 1-3); override individual fields per case.
_MAPPING_OVERRIDE_DEFAULTS = dict(
    anilist_id=100,
    anilist_episode_number_from=1,
    anilist_episode_number_to=3,
    tvdb_series_id=200,
    tvdb_season_number=1,
    tvdb_episode_number_from=1,
    tvdb_episode_number_to=3,
    granularity=1,
    mode=MappingOverrideMode.ALWAYS,
)


def make_mapping_request(**overrides):
    from api.schemas.mapping_schemas import MappingOverrideRequest
    return MappingOverrideRequest(**{**_MAPPING_OVERRIDE_DEFAULTS, **overrides})


def make_mapping_override(override_id: int = 1, **overrides) -> MappingOverride:
    # SQLAlchemy defaults don't apply pre-flush, so every column is set explicitly.
    override = MappingOverride()
    for key, value in {"id": override_id, **_MAPPING_OVERRIDE_DEFAULTS, **overrides}.items():
        setattr(override, key, value)
    return override


def make_tvdb_series(title: str = "Series",
                     english_title: str | None = "Series EN",
                     image_url: str | None = "http://img/series.jpg") -> TVDBSeries:
    return TVDBSeries.from_dict({
        "name": title,
        "eng_translation": {"name": english_title} if english_title is not None else {},
        "image": image_url,
    })


def make_service_status(name: str = "qBittorrent",
                        code: ExternalServiceCode = ExternalServiceCode.QBIT,
                        **kwargs) -> ServiceStatus:
    return ServiceStatus(name, code, **kwargs)
