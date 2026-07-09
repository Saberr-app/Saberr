from typing import Literal

from pydantic import BaseModel

from constants import (
    AnilistTitleLanguage,
    Encoding,
    ReleaseCriteriaProperty,
    Resolution,
    VideoSource, AnilistScoreFormat, RSSCategory,
)
from api.schemas import digit_str, int_in_range, cached_asset, NonEmptyString
from system import UNSET


class GeneralSettings(BaseModel):
    set_download_as_failed_after_minutes: int_in_range(ge=5)
    set_processing_as_failed_after_minutes: int_in_range(ge=1)
    timezone: NonEmptyString
    published_url: NonEmptyString | None = None
    anilist_preferred_title_language: AnilistTitleLanguage


class ProfileSettings(BaseModel):
    preferred_release_groups: list[NonEmptyString]
    preferred_encodings: list[Encoding]
    preferred_resolutions: list[Resolution]
    preferred_language_codes: list[NonEmptyString]
    preferred_sources: list[VideoSource]
    language_codes_restricted: bool
    sources_restricted: bool
    accept_release_upgrades: bool
    priorities_sorted: list[ReleaseCriteriaProperty]


class AnilistLoginRequest(BaseModel):
    anilist_user_token: NonEmptyString


class AnilistUserData(BaseModel):
    username: str
    avatar: cached_asset()
    banner: cached_asset()
    current_anime_count: int
    planning_anime_count: int
    completed_anime_count: int
    mean_score: float
    site_url: str
    moderator_roles: list[str] | None
    score_format: AnilistScoreFormat


class QBitBaseServiceSettings(BaseModel):
    qbit_base_url: NonEmptyString | None
    qbit_username: NonEmptyString | None
    qbit_password: NonEmptyString | None = UNSET  # keep the password as is when field is not sent


class QBitServiceSettings(QBitBaseServiceSettings):
    qbit_remote_path_mapping_remote_path: NonEmptyString | None = None
    qbit_remote_path_mapping_local_path: NonEmptyString | None = None
    torrent_category: NonEmptyString | None = None
    staging_directory: NonEmptyString | None = None
    organize_downloads: bool
    apply_release_group_as_torrent_tag: bool
    apply_encoding_as_torrent_tag: bool
    apply_resolution_as_torrent_tag: bool
    apply_language_code_as_torrent_tag: bool
    apply_anime_title_as_torrent_tag: bool


class RSSSettings(BaseModel):
    auto_download: bool
    rss_check_frequency: int_in_range(ge=30)  # seconds
    rss_category: RSSCategory


class ProcessingSettings(BaseModel):
    default_destination_directory: NonEmptyString | None = None
    default_show_directory_name_format: NonEmptyString
    default_season_directory_name_format: NonEmptyString
    default_raw_episode_file_name_format: NonEmptyString
    default_episode_file_name_format: NonEmptyString
    default_titleless_episode_file_name_format: NonEmptyString
    tvdb_structure_enabled_default: bool


class DiscordSettings(BaseModel):
    notifications_discord_webhook_url: NonEmptyString | None = None
    discord_webhook_username: NonEmptyString | None
    discord_webhook_avatar_url: NonEmptyString | None
    discord_notify_on_login: bool
    discord_notify_on_download_processed: bool
    discord_notify_on_upgrade_download_processed: bool
    discord_notify_on_download_failed: bool
    discord_user_id: digit_str() | None = None


class DiscordWebhookTest(BaseModel):
    webhook_url: NonEmptyString


class SettingsResponse(BaseModel):

    class AnilistSettingsState(BaseModel):
        anilist_username: str | None
        anilist_user_token: Literal["SET", "UNSET"]
        anilist_user_data: AnilistUserData | None

    class Metadata(BaseModel):
        show_directory_formatting_tokens: dict[str, str]
        season_directory_formatting_tokens: dict[str, str]
        raw_episode_formatting_tokens: dict[str, str]
        full_episode_formatting_tokens: dict[str, str]
        titleless_episode_formatting_tokens: dict[str, str]
        available_release_groups: list[str]

    class QBitServiceSettingsState(QBitServiceSettings):
        qbit_password: Literal["SET", "UNSET"]

    general: GeneralSettings
    profile: ProfileSettings
    anilist: AnilistSettingsState
    qbit: QBitServiceSettingsState
    rss: RSSSettings
    processing: ProcessingSettings
    discord: DiscordSettings
    meta: Metadata
