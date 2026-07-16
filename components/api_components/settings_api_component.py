from app_state import global_status
from common.context_helpers import create_task
from common.decorators import api_component
from common.exceptions import ValidationException
from components import BaseComponent
from components.settings_component import SettingsComponent
from components.operational_components.tracked_anime_profile_component import TrackedAnimeProfileComponent
from components.service_components.anilist_list_component import AnilistListComponent
from config import config
from constants import (SettingsCode, AnilistTitleLanguage, SHOW_DIRECTORY_FORMATTING_TOKEN_VALUE_NAME_MAP,
                       SEASON_DIRECTORY_FORMATTING_TOKEN_VALUE_NAME_MAP, EpisodeFormattingToken,
                       EPISODE_FORMATTING_TOKEN_VALUE_NAME_MAP, AnilistAnimeUserStatus, ExternalServiceCode)
from api.schemas.settings_schemas import (SettingsResponse, GeneralSettings, ProfileSettings, QBitServiceSettings,
                                          RSSSettings, ProcessingSettings, DiscordSettings,
                                          AnilistLoginRequest, DiscordWebhookTest, AnilistUserData,
                                          QBitBaseServiceSettings)
from services.anilist_service import AnilistService
from services.discord_webhook_service import DiscordWebhookService
from services.qbit_service import QBitService
from system import UNSET
from utils.helpers.text_helpers import clean_path_name


class SettingsAPIComponent(BaseComponent):

    def __init__(self):
        super().__init__()
        self._settings_component = SettingsComponent()
        self._tracked_anime_profile_component = TrackedAnimeProfileComponent()
        self._anilist_list_component = AnilistListComponent()

    @api_component
    async def get_settings(self) -> SettingsResponse:
        user_settings = config.user_settings
        default_profile = await self._tracked_anime_profile_component.get_default_tracked_anime_profile()

        return SettingsResponse(
            general=self._general_settings(user_settings),
            profile=self._profile_settings(default_profile),
            anilist=self._anilist_settings_state(user_settings),
            qbit=self._qbit_service_settings(user_settings),
            rss=self._rss_settings(user_settings),
            processing=self._processing_settings(user_settings),
            discord=self._discord_settings(user_settings),
            meta=SettingsResponse.Metadata(
                show_directory_formatting_tokens={v: k for k, v in
                                                  SHOW_DIRECTORY_FORMATTING_TOKEN_VALUE_NAME_MAP.items()},
                season_directory_formatting_tokens={v: k for k, v in
                                                    SEASON_DIRECTORY_FORMATTING_TOKEN_VALUE_NAME_MAP.items()},
                raw_episode_formatting_tokens={EPISODE_FORMATTING_TOKEN_VALUE_NAME_MAP[value]: value for value in
                                               EpisodeFormattingToken.raw_episode_tokens()},
                full_episode_formatting_tokens={EPISODE_FORMATTING_TOKEN_VALUE_NAME_MAP[value]: value for value in
                                                EpisodeFormattingToken.full_episode_tokens()},
                titleless_episode_formatting_tokens={EPISODE_FORMATTING_TOKEN_VALUE_NAME_MAP[value]: value for value in
                                                     EpisodeFormattingToken.titleless_episode_tokens()},
                available_release_groups=list(config.release_groups_map)
            )
        )

    @api_component
    async def update_general_settings(self, body: GeneralSettings) -> GeneralSettings:
        await self._settings_component.update_settings({
            SettingsCode.SET_DOWNLOAD_AS_FAILED_AFTER_MINUTES: body.set_download_as_failed_after_minutes,
            SettingsCode.SET_PROCESSING_AS_FAILED_AFTER_MINUTES: body.set_processing_as_failed_after_minutes,
            SettingsCode.TIMEZONE: body.timezone,
            SettingsCode.PUBLISHED_URL: body.published_url,
            SettingsCode.ANILIST_PREFERRED_TITLE_LANGUAGE: body.anilist_preferred_title_language,
        })
        return self._general_settings(config.user_settings)

    @api_component
    async def update_profile_settings(self, body: ProfileSettings) -> ProfileSettings:
        # The default profile is id=1 (seeded on startup).
        await self._tracked_anime_profile_component.update_tracked_anime_profile(
            profile_id=1,
            preferred_release_groups=body.preferred_release_groups,
            preferred_encodings=body.preferred_encodings,
            preferred_resolutions=body.preferred_resolutions,
            preferred_language_codes=body.preferred_language_codes,
            preferred_sources=body.preferred_sources,
            language_codes_restricted=body.language_codes_restricted,
            sources_restricted=body.sources_restricted,
            accept_release_upgrades=body.accept_release_upgrades,
            priorities_sorted=body.priorities_sorted,
        )
        return self._profile_settings(await self._tracked_anime_profile_component.get_default_tracked_anime_profile())

    @api_component
    async def update_qbit_service_settings(self,
                                           body: QBitServiceSettings) -> SettingsResponse.QBitServiceSettingsState:
        from app_state import downstream_healthcheck_workers
        if body.qbit_remote_path_mapping_remote_path and body.qbit_remote_path_mapping_local_path:
            qbit_remote_path_mapping = (body.qbit_remote_path_mapping_remote_path,
                                        body.qbit_remote_path_mapping_local_path)
        elif body.qbit_remote_path_mapping_remote_path or body.qbit_remote_path_mapping_local_path:
            raise ValidationException("Both remote and local paths must be specified"
                                      " for the qBittorrent remote path mapping.")
        else:
            qbit_remote_path_mapping = None
        await self._settings_component.update_settings({
            SettingsCode.QBIT_BASE_URL: body.qbit_base_url,
            SettingsCode.QBIT_USERNAME: body.qbit_username,
            SettingsCode.QBIT_REMOTE_PATH_MAPPING: qbit_remote_path_mapping,
            SettingsCode.TORRENT_CATEGORY: body.torrent_category,
            SettingsCode.STAGING_DIRECTORY: clean_path_name(body.staging_directory) if body.staging_directory else None,
            SettingsCode.ORGANIZE_DOWNLOADS: body.organize_downloads,
            SettingsCode.APPLY_RELEASE_GROUP_AS_TORRENT_TAG: body.apply_release_group_as_torrent_tag,
            SettingsCode.APPLY_ENCODING_AS_TORRENT_TAG: body.apply_encoding_as_torrent_tag,
            SettingsCode.APPLY_RESOLUTION_AS_TORRENT_TAG: body.apply_resolution_as_torrent_tag,
            SettingsCode.APPLY_LANGUAGE_CODE_AS_TORRENT_TAG: body.apply_language_code_as_torrent_tag,
            SettingsCode.APPLY_ANIME_TITLE_AS_TORRENT_TAG: body.apply_anime_title_as_torrent_tag,
        } | ({SettingsCode.QBIT_PASSWORD: body.qbit_password} if body.qbit_password is not UNSET else {}))
        create_task(downstream_healthcheck_workers.force_check(ExternalServiceCode.QBIT))
        global_status.services_status_changed()
        return self._qbit_service_settings(config.user_settings)

    @api_component
    async def update_rss_settings(self, body: RSSSettings) -> RSSSettings:
        await self._settings_component.update_settings({
            SettingsCode.AUTO_DOWNLOAD: body.auto_download,
            SettingsCode.RSS_CHECK_FREQUENCY: body.rss_check_frequency,
            SettingsCode.RSS_CATEGORY: body.rss_category,
        })
        global_status.services_status_changed()
        return self._rss_settings(config.user_settings)

    @api_component
    async def update_processing_settings(self, body: ProcessingSettings) -> ProcessingSettings:
        await self._settings_component.update_settings({
            SettingsCode.DEFAULT_DESTINATION_DIRECTORY: body.default_destination_directory,
            SettingsCode.DEFAULT_SHOW_DIRECTORY_NAME_FORMAT: body.default_show_directory_name_format,
            SettingsCode.DEFAULT_SEASON_DIRECTORY_NAME_FORMAT: body.default_season_directory_name_format,
            SettingsCode.DEFAULT_RAW_EPISODE_FILE_NAME_FORMAT: body.default_raw_episode_file_name_format,
            SettingsCode.DEFAULT_EPISODE_FILE_NAME_FORMAT: body.default_episode_file_name_format,
            SettingsCode.DEFAULT_TITLELESS_EPISODE_FILE_NAME_FORMAT: body.default_titleless_episode_file_name_format,
            SettingsCode.TVDB_STRUCTURE_ENABLED_DEFAULT: body.tvdb_structure_enabled_default,
        })
        return self._processing_settings(config.user_settings)

    @api_component
    async def update_discord_settings(self, body: DiscordSettings) -> DiscordSettings:
        from app_state import downstream_healthcheck_workers
        await self._settings_component.update_settings({
            SettingsCode.NOTIFICATIONS_DISCORD_WEBHOOK_URL:
                body.notifications_discord_webhook_url,
            SettingsCode.DISCORD_WEBHOOK_USERNAME:
                body.discord_webhook_username,
            SettingsCode.DISCORD_WEBHOOK_AVATAR_URL:
                body.discord_webhook_avatar_url,
            SettingsCode.DISCORD_NOTIFY_ON_LOGIN:
                body.discord_notify_on_login,
            SettingsCode.DISCORD_NOTIFY_ON_DOWNLOAD_PROCESSED:
                body.discord_notify_on_download_processed,
            SettingsCode.DISCORD_NOTIFY_ON_UPGRADE_DOWNLOAD_PROCESSED:
                body.discord_notify_on_upgrade_download_processed,
            SettingsCode.DISCORD_NOTIFY_ON_DOWNLOAD_FAILED:
                body.discord_notify_on_download_failed,
            SettingsCode.DISCORD_USER_ID:
                body.discord_user_id,
        })
        create_task(downstream_healthcheck_workers.force_check(ExternalServiceCode.NOTIFICATIONS_DISCORD_WEBHOOK))
        global_status.services_status_changed()
        return self._discord_settings(config.user_settings)

    # noinspection PyMethodMayBeStatic
    def _general_settings(self, user_settings) -> GeneralSettings:
        return GeneralSettings(
            set_download_as_failed_after_minutes=user_settings.set_download_as_failed_after_minutes,
            set_processing_as_failed_after_minutes=user_settings.set_processing_as_failed_after_minutes,
            timezone=user_settings.timezone,
            published_url=user_settings.published_url,
            anilist_preferred_title_language=user_settings.anilist_preferred_title_language,
        )

    # noinspection PyMethodMayBeStatic
    def _profile_settings(self, profile) -> ProfileSettings:
        return ProfileSettings(
            preferred_release_groups=profile.preferred_release_groups,
            preferred_encodings=profile.preferred_encodings,
            preferred_resolutions=profile.preferred_resolutions,
            preferred_language_codes=profile.preferred_language_codes,
            preferred_sources=profile.preferred_sources,
            language_codes_restricted=profile.language_codes_restricted,
            sources_restricted=profile.sources_restricted,
            accept_release_upgrades=profile.accept_release_upgrades,
            priorities_sorted=profile.priorities_sorted,
        )

    # noinspection PyMethodMayBeStatic
    def _anilist_settings_state(self, user_settings) -> SettingsResponse.AnilistSettingsState:
        return SettingsResponse.AnilistSettingsState(
            anilist_username=user_settings.anilist_username,
            anilist_user_token="SET" if user_settings.anilist_user_token is not None else "UNSET",
            anilist_user_data=self._build_anilist_user_data_response(user_settings.anilist_user_data)
        )

    # noinspection PyMethodMayBeStatic
    def _qbit_service_settings(self, user_settings) -> SettingsResponse.QBitServiceSettingsState:
        (qbit_remote_path_mapping_remote_path, qbit_remote_path_mapping_local_path) = \
            user_settings.qbit_remote_path_mapping if user_settings.qbit_remote_path_mapping else (None, None)
        return SettingsResponse.QBitServiceSettingsState(
            qbit_base_url=user_settings.qbit_base_url,
            qbit_username=user_settings.qbit_username,
            qbit_password="SET" if user_settings.qbit_password is not None else "UNSET",
            qbit_remote_path_mapping_remote_path=qbit_remote_path_mapping_remote_path,
            qbit_remote_path_mapping_local_path=qbit_remote_path_mapping_local_path,
            torrent_category=user_settings.torrent_category,
            staging_directory=user_settings.staging_directory,
            organize_downloads=user_settings.organize_downloads,
            apply_release_group_as_torrent_tag=user_settings.apply_release_group_as_torrent_tag,
            apply_encoding_as_torrent_tag=user_settings.apply_encoding_as_torrent_tag,
            apply_resolution_as_torrent_tag=user_settings.apply_resolution_as_torrent_tag,
            apply_language_code_as_torrent_tag=user_settings.apply_language_code_as_torrent_tag,
            apply_anime_title_as_torrent_tag=user_settings.apply_anime_title_as_torrent_tag,
        )

    # noinspection PyMethodMayBeStatic
    def _rss_settings(self, user_settings) -> RSSSettings:
        return RSSSettings(
            auto_download=user_settings.auto_download,
            rss_check_frequency=user_settings.rss_check_frequency,
            rss_category=user_settings.rss_category
        )

    # noinspection PyMethodMayBeStatic
    def _processing_settings(self, user_settings) -> ProcessingSettings:
        return ProcessingSettings(
            default_destination_directory=user_settings.default_destination_directory,
            default_show_directory_name_format=user_settings.default_show_directory_name_format,
            default_season_directory_name_format=user_settings.default_season_directory_name_format,
            default_raw_episode_file_name_format=user_settings.default_raw_episode_file_name_format,
            default_episode_file_name_format=user_settings.default_episode_file_name_format,
            default_titleless_episode_file_name_format=user_settings.default_titleless_episode_file_name_format,
            tvdb_structure_enabled_default=user_settings.tvdb_structure_enabled_default,
        )

    # noinspection PyMethodMayBeStatic
    def _discord_settings(self, user_settings) -> DiscordSettings:
        return DiscordSettings(
            notifications_discord_webhook_url=user_settings.notifications_discord_webhook_url,
            discord_webhook_username=user_settings.discord_webhook_username,
            discord_webhook_avatar_url=user_settings.discord_webhook_avatar_url,
            discord_notify_on_login=user_settings.discord_notify_on_login,
            discord_notify_on_download_processed=user_settings.discord_notify_on_download_processed,
            discord_notify_on_upgrade_download_processed=user_settings.discord_notify_on_upgrade_download_processed,
            discord_notify_on_download_failed=user_settings.discord_notify_on_download_failed,
            discord_user_id=user_settings.discord_user_id,
        )

    @api_component
    async def check_anilist_authentication(self, body: AnilistLoginRequest) -> AnilistUserData:
        user_data = await AnilistService().get_user_data(token=body.anilist_user_token)
        return self._build_anilist_user_data_response(user_data)

    @api_component
    async def check_qbit_connection(self, body: QBitBaseServiceSettings):
        qbit_password = body.qbit_password if body.qbit_password is not UNSET else config.user_settings.qbit_password
        await QBitService(base_url=body.qbit_base_url,
                          username=body.qbit_username,
                          password=qbit_password).healthcheck(use_new_session=True)

    @api_component
    async def test_discord_webhook_connection(self, body: DiscordWebhookTest):
        await DiscordWebhookService().healthcheck(body.webhook_url)

    @api_component
    async def authenticate_anilist(self, body: AnilistLoginRequest) -> AnilistUserData:
        from app_state import downstream_healthcheck_workers
        user_data = await AnilistService().get_user_data(token=body.anilist_user_token)
        username = user_data['name']
        preferred_title_language = AnilistTitleLanguage(user_data['options']['titleLanguage'].split('_')[0].title())
        await self._settings_component.update_settings(
            {SettingsCode.ANILIST_USER_TOKEN: body.anilist_user_token,
             SettingsCode.ANILIST_USERNAME: username,
             SettingsCode.ANILIST_PREFERRED_TITLE_LANGUAGE: preferred_title_language,
             SettingsCode.ANILIST_USER_DATA: user_data}
        )
        create_task(downstream_healthcheck_workers.force_check(ExternalServiceCode.ANILIST))
        await self._anilist_list_component.fetch_user_anime_list(fetch_full_anime_data=True)
        global_status.services_status_changed()
        return self._build_anilist_user_data_response(user_data)

    @api_component
    async def logout_from_anilist(self):
        from app_state import downstream_healthcheck_workers
        await self._settings_component.update_settings({SettingsCode.ANILIST_USERNAME: None,
                                                        SettingsCode.ANILIST_USER_TOKEN: None,
                                                        SettingsCode.ANILIST_USER_DATA: None})
        create_task(downstream_healthcheck_workers.force_check(ExternalServiceCode.ANILIST))
        global_status.services_status_changed()
        await self._anilist_list_component.delete_user_anime_list()

    @staticmethod
    def _build_anilist_user_data_response(user_anilist_data: dict) -> AnilistUserData | None:
        if not user_anilist_data:
            return None
        statuses = {
            item["status"]: item["count"]
            for item in user_anilist_data["statistics"]["anime"]["statuses"]
        }

        return AnilistUserData(
            username=user_anilist_data["name"],
            avatar=user_anilist_data.get("avatar", {}).get("medium"),
            banner=user_anilist_data.get("bannerImage"),
            current_anime_count=statuses.get(AnilistAnimeUserStatus.CURRENT.value, 0),
            planning_anime_count=statuses.get(AnilistAnimeUserStatus.PLANNING.value, 0),
            completed_anime_count=statuses.get(AnilistAnimeUserStatus.COMPLETED.value, 0),
            mean_score=round(user_anilist_data["statistics"]["anime"]["meanScore"]),
            site_url=user_anilist_data["siteUrl"],
            moderator_roles=user_anilist_data.get("moderatorRoles"),
            score_format=user_anilist_data["mediaListOptions"]["scoreFormat"]
        )
