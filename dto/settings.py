import re
from dataclasses import dataclass

from constants import ReleaseGroupFilterType, Encoding, Resolution, ReleaseGroupEpisodeNumberingAffinity, \
    ReleaseTitlePart, SettingsCode, AnilistTitleLanguage, AnilistScoreFormat, RSSCategory


@dataclass
class UserSettings:
    anilist_username: str | None
    anilist_user_token: str | None
    anilist_user_data: dict | None

    qbit_base_url: str | None
    qbit_username: str | None
    qbit_password: str | None
    qbit_remote_path_mapping: tuple[str, str] | None

    default_destination_directory: str | None
    default_show_directory_name_format: str
    default_season_directory_name_format: str
    default_raw_episode_file_name_format: str
    default_episode_file_name_format: str
    default_titleless_episode_file_name_format: str

    tvdb_structure_enabled_default: bool
    torrent_category: str | None
    staging_directory: str | None
    organize_downloads: bool
    apply_release_group_as_torrent_tag: bool
    apply_encoding_as_torrent_tag: bool
    apply_resolution_as_torrent_tag: bool
    apply_language_code_as_torrent_tag: bool
    apply_anime_title_as_torrent_tag: bool
    auto_download: bool
    rss_check_frequency: int
    rss_category: RSSCategory
    set_download_as_failed_after_minutes: int
    set_processing_as_failed_after_minutes: int
    notifications_discord_webhook_url: str | None
    discord_webhook_username: str
    discord_webhook_avatar_url: str
    discord_notify_on_login: bool
    discord_notify_on_download_processed: bool
    discord_notify_on_upgrade_download_processed: bool
    discord_notify_on_download_failed: bool
    discord_user_id: str | None

    timezone: str
    anilist_preferred_title_language: AnilistTitleLanguage
    published_url: str | None

    @classmethod
    def from_dict(cls, data: dict) -> 'UserSettings':
        key_value = {}
        for key, value in data.items():
            if key == SettingsCode.ANILIST_PREFERRED_TITLE_LANGUAGE.value:
                key_value[key.lower()] = AnilistTitleLanguage(value)
            elif key == SettingsCode.RSS_CATEGORY.value:
                key_value[key.lower()] = RSSCategory(value)
            elif key in [SettingsCode.DISCORD_USER_ID.value, SettingsCode.QBIT_USERNAME.value,
                         SettingsCode.QBIT_PASSWORD.value, SettingsCode.ANILIST_USER_TOKEN.value]:
                key_value[key.lower()] = str(value) if value is not None else None
            elif key == SettingsCode.QBIT_REMOTE_PATH_MAPPING.value and value is not None:
                key_value[key.lower()] = tuple(value)
            else:
                key_value[key.lower()] = value
        return cls(
            **key_value
        )

    def to_dict(self) -> dict:
        hidden_settings = [SettingsCode.ANILIST_USER_TOKEN.value, SettingsCode.QBIT_PASSWORD.value]
        settings = {}
        for setting in SettingsCode:
            if setting.value in hidden_settings:
                settings[setting.value] = "SET" if getattr(self, setting.value.lower()) is not None else "UNSET"
            else:
                settings[setting.value] = getattr(self, setting.value.lower())
        return settings

    @property
    def user_score_format(self) -> AnilistScoreFormat | None:
        if not self.anilist_user_data:
            return None
        return AnilistScoreFormat(self.anilist_user_data["mediaListOptions"]["scoreFormat"])


@dataclass(frozen=True, repr=False)
class ReleaseGroup:
    name: str
    submitter: str
    unique_filter: 'ReleaseGroupFilter'
    regexes: list['ReleaseRegex']
    default_encoding: Encoding
    default_resolution: Resolution
    default_language_code: str
    batch_keyword: str | None
    episode_numbering_affinity: ReleaseGroupEpisodeNumberingAffinity

    @classmethod
    def from_dict(cls, name: str, data: dict) -> 'ReleaseGroup':
        return cls(
            name=name,
            submitter=data["submitter"],
            unique_filter=ReleaseGroupFilter.from_dict(data["unique_filter"]),
            regexes=ReleaseRegex.many_from_dict(data["regex"]),
            default_encoding=Encoding(data["default_encoding"]),
            default_resolution=Resolution(data["default_resolution"]),
            default_language_code=data["default_language_code"],
            batch_keyword=data.get("batch_keyword"),
            episode_numbering_affinity=ReleaseGroupEpisodeNumberingAffinity(data["episode_numbering_affinity"])
        )

    @classmethod
    def many_from_dict(cls, release_groups_data: dict) -> list['ReleaseGroup']:
        release_groups = []
        for name, data in release_groups_data.items():
            release_group = cls.from_dict(name, data)
            release_groups.append(release_group)
        return release_groups

    def __repr__(self):
        return f"ReleaseGroup('{self.name}')"


@dataclass(frozen=True)
class ReleaseGroupFilter:
    filter_type: ReleaseGroupFilterType
    value: str

    @classmethod
    def from_dict(cls, data: dict) -> 'ReleaseGroupFilter':
        filter_type, value = data.popitem()
        assert filter_type in ReleaseGroupFilterType.as_list(), f"Invalid filter type: {filter_type}"
        return cls(ReleaseGroupFilterType(filter_type), value)

    def match_title(self, title: str) -> bool:
        if self.filter_type == ReleaseGroupFilterType.STARTS_WITH:
            return title.lower().startswith(self.value.lower())
        elif self.filter_type == ReleaseGroupFilterType.CONTAINS:
            return self.value.lower() in title.lower()
        else:
            raise ValueError(f"Invalid filter type: {self.filter_type}")


@dataclass(frozen=True)
class ReleaseRegex:
    pattern: re.Pattern
    required_pattern_groups: list[ReleaseTitlePart]

    @classmethod
    def many_from_dict(cls, data: list[dict]) -> list['ReleaseRegex']:
        return [
            cls(
                pattern=re.compile(regex["pattern"]),
                required_pattern_groups=[ReleaseTitlePart(required_pattern_group)
                                         for required_pattern_group in regex["required_pattern_groups"]],
            ) for regex in data
        ]
