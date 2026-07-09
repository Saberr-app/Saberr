from typing import Any

import pytz

from common.db import get_session
from common.exceptions import InvalidSettingValueException
from components import BaseComponent
from config import config
from constants import SettingsCode, SETTINGS_CODE_FRIENDLY_NAME_MAP, ShowDirectoryFormattingToken, \
    SeasonDirectoryFormattingToken, EpisodeFormattingToken, AnilistTitleLanguage, RSSCategory
from app_state import global_status
from repositories.settings_repo import SettingsRepo
from utils.helpers.path_helpers import is_valid_directory_path
from utils.helpers.text_helpers import is_valid_url, validate_format_tokens
from utils.helpers.type_helpers import require_str, require_bool, require_int, require_digit_str, require_iterable


class SettingsComponent(BaseComponent):
    SETTING_CODES_IGNORE_AUDIT_LOG = {
        SettingsCode.ANILIST_USER_DATA,
        SettingsCode.ANILIST_USER_TOKEN,
    }
    SETTING_CODES_REDACT_VALUE_AUDIT_LOG = {
        SettingsCode.QBIT_PASSWORD,
    }

    def __init__(self):
        super().__init__()
        from components.audit_log_component import AuditLogComponent
        self._audit_log_component = AuditLogComponent()

    # noinspection PyMethodMayBeStatic
    async def get_settings(self) -> dict:
        return config.user_settings.to_dict()

    async def update_settings(self, code_values: dict[SettingsCode, Any]):
        for code, value in code_values.items():
            code_values[code] = self.validate_setting_value(code, value)

        value_updated = False
        for code, value in code_values.items():
            attr_name = code.value.lower()
            old_value = getattr(config.user_settings, attr_name)
            if value == old_value:
                continue

            await SettingsRepo(get_session()).update_setting(code, data=value)
            setattr(config.user_settings, attr_name, value)

            if code not in self.SETTING_CODES_IGNORE_AUDIT_LOG:
                if code in self.SETTING_CODES_REDACT_VALUE_AUDIT_LOG:
                    old_log_value = "REDACTED" if old_value else "Not set"
                    log_value = "REDACTED"
                else:
                    old_log_value = old_value
                    log_value = value
                await self._audit_log_component.log_setting_changed(
                    setting_name=SETTINGS_CODE_FRIENDLY_NAME_MAP[code],
                    old_value=old_log_value,
                    new_value=log_value,
                )
            value_updated = True

        if value_updated:
            global_status.settings_updated()

    @staticmethod
    def validate_setting_value(code: SettingsCode, value: Any) -> Any:
        try:
            match code:
                case SettingsCode.ANILIST_USERNAME:
                    require_str(value, nullable=True, max_length=20, new_lines_allowed=False)

                case SettingsCode.QBIT_BASE_URL:
                    require_str(value, nullable=True, new_lines_allowed=False)
                    if value and not is_valid_url(value):
                        raise InvalidSettingValueException(f"Invalid URL: {value}")

                case SettingsCode.QBIT_USERNAME:
                    require_str(value, nullable=True, new_lines_allowed=False)

                case SettingsCode.QBIT_PASSWORD:
                    require_str(value, nullable=True, new_lines_allowed=False)

                case SettingsCode.QBIT_REMOTE_PATH_MAPPING:
                    require_iterable(value, nullable=True, size=2)

                case SettingsCode.DEFAULT_DESTINATION_DIRECTORY:
                    require_str(value, nullable=True, new_lines_allowed=False)
                    if value and not is_valid_directory_path(value, validate_writability=False):
                        raise InvalidSettingValueException(f"Invalid/inaccessible destination directory: {value}")

                case SettingsCode.DEFAULT_SHOW_DIRECTORY_NAME_FORMAT:
                    require_str(value)
                    validate_format_tokens(text=value, allowed_tokens=ShowDirectoryFormattingToken.as_list())

                case SettingsCode.DEFAULT_SEASON_DIRECTORY_NAME_FORMAT:
                    require_str(value)
                    validate_format_tokens(text=value, allowed_tokens=SeasonDirectoryFormattingToken.as_list())

                case SettingsCode.DEFAULT_RAW_EPISODE_FILE_NAME_FORMAT:
                    require_str(value)
                    validate_format_tokens(text=value, allowed_tokens=EpisodeFormattingToken.raw_episode_tokens())

                case SettingsCode.DEFAULT_EPISODE_FILE_NAME_FORMAT:
                    require_str(value)
                    validate_format_tokens(text=value, allowed_tokens=EpisodeFormattingToken.full_episode_tokens())

                case SettingsCode.DEFAULT_TITLELESS_EPISODE_FILE_NAME_FORMAT:
                    require_str(value)
                    validate_format_tokens(text=value, allowed_tokens=EpisodeFormattingToken.titleless_episode_tokens())

                case SettingsCode.TVDB_STRUCTURE_ENABLED_DEFAULT:
                    require_bool(value)

                case SettingsCode.TORRENT_CATEGORY:
                    require_str(value, nullable=True)

                case SettingsCode.STAGING_DIRECTORY:
                    require_str(value, nullable=True)

                case SettingsCode.ORGANIZE_DOWNLOADS:
                    require_bool(value)

                case SettingsCode.APPLY_RELEASE_GROUP_AS_TORRENT_TAG:
                    require_bool(value)

                case SettingsCode.APPLY_ENCODING_AS_TORRENT_TAG:
                    require_bool(value)

                case SettingsCode.APPLY_RESOLUTION_AS_TORRENT_TAG:
                    require_bool(value)

                case SettingsCode.APPLY_LANGUAGE_CODE_AS_TORRENT_TAG:
                    require_bool(value)

                case SettingsCode.APPLY_ANIME_TITLE_AS_TORRENT_TAG:
                    require_bool(value)

                case SettingsCode.AUTO_DOWNLOAD:
                    require_bool(value)

                case SettingsCode.RSS_CHECK_FREQUENCY:
                    require_int(value, minimum_value=30)

                case SettingsCode.RSS_CATEGORY:
                    if isinstance(value, str):
                        if value not in RSSCategory.as_list():
                            raise InvalidSettingValueException(f"Invalid rss category: {value}")
                        else:
                            value = RSSCategory(value)

                case SettingsCode.SET_DOWNLOAD_AS_FAILED_AFTER_MINUTES:
                    require_int(value, minimum_value=5)

                case SettingsCode.SET_PROCESSING_AS_FAILED_AFTER_MINUTES:
                    require_int(value, minimum_value=1)

                case SettingsCode.NOTIFICATIONS_DISCORD_WEBHOOK_URL:
                    require_str(value, nullable=True)
                    if value and not is_valid_url(value):
                        raise InvalidSettingValueException(f"Invalid URL: {value}")

                case SettingsCode.DISCORD_WEBHOOK_USERNAME:
                    require_str(value, min_length=1, max_length=80, nullable=True)

                case SettingsCode.DISCORD_WEBHOOK_AVATAR_URL:
                    require_str(value, nullable=True)
                    if value and not is_valid_url(value):
                        raise InvalidSettingValueException(f"Invalid URL: {value}")

                case SettingsCode.DISCORD_NOTIFY_ON_LOGIN:
                    require_bool(value, nullable=True)

                case SettingsCode.DISCORD_NOTIFY_ON_DOWNLOAD_PROCESSED:
                    require_bool(value, nullable=True)

                case SettingsCode.DISCORD_NOTIFY_ON_UPGRADE_DOWNLOAD_PROCESSED:
                    require_bool(value, nullable=True)

                case SettingsCode.DISCORD_NOTIFY_ON_DOWNLOAD_FAILED:
                    require_bool(value, nullable=True)

                case SettingsCode.DISCORD_USER_ID:
                    require_digit_str(value, nullable=True)

                case SettingsCode.TIMEZONE:
                    require_str(value)
                    if value not in pytz.all_timezones:
                        raise InvalidSettingValueException(f"Invalid timezone: {value}")

                case SettingsCode.ANILIST_PREFERRED_TITLE_LANGUAGE:
                    if isinstance(value, str):
                        if value not in AnilistTitleLanguage.as_list():
                            raise InvalidSettingValueException(f"Invalid title language: {value}")
                        else:
                            value = AnilistTitleLanguage(value)

                case SettingsCode.PUBLISHED_URL:
                    require_str(value, nullable=True, new_lines_allowed=False)
                    if value and not is_valid_url(value):
                        raise InvalidSettingValueException(f"Invalid URL: {value}")
                case SettingsCode.ANILIST_USER_DATA | SettingsCode.ANILIST_USER_TOKEN:
                    pass
                case _:
                    raise InvalidSettingValueException(f"Unknown setting: {code}")
        except (TypeError, ValueError) as e:
            raise InvalidSettingValueException(f"Invalid value for setting: {code}") from e

        return value
