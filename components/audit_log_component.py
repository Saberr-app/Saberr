from datetime import datetime
from typing import TYPE_CHECKING, Any

from common.context_helpers import get_context_id
from common.db import get_session
from common.decorators import require_db_session
from components import BaseComponent
from constants import AuditLogCategory, AuditLogCode, AUDIT_LOG_CODE_TO_CATEGORY_MAP, Enum, SortDirection, \
    MappingOverrideMode
from dto.nyaa_item import NyaaItem
from dto.orm_models import AuditLog, Torrent, TrackedAnimeEpisode, TrackedAnime, TorrentDownload, \
    TrackedAnimeReleaseGroupPreferences, TrackedAnimeProfile
from repositories.audit_log_repo import AuditLogRepo

if TYPE_CHECKING:
    from workers.downstream_healthcheck_workers import ServiceStatus


def _create_audit_log(func):
    async def wrapper(*args, **kwargs):
        items = [item async for item in func(*args, **kwargs)]
        if len(items) != 3:
            raise ValueError("Audit log generators must yield exactly 3 items: code, text, data")
        await AuditLogRepo(get_session()).create_audit_log(
            code=items[0],
            category=AUDIT_LOG_CODE_TO_CATEGORY_MAP[items[0]],
            text=items[1],
            data=items[2],
            context_id=get_context_id()
        )
    return wrapper


class AuditLogComponent(BaseComponent):

    # noinspection PyMethodMayBeStatic
    async def get_audit_logs(self,
                             categories: list[AuditLogCategory] | None = None,
                             codes: list[AuditLogCode] | None = None,
                             text_query: str | None = None,
                             data_query: str | None = None,
                             context_id: str | None = None,
                             created_after: datetime | None = None,
                             created_before: datetime | None = None,
                             sort_direction: SortDirection = SortDirection.DESC,
                             limit: int | None = None,
                             offset: int | None = None) -> list[AuditLog]:
        return await AuditLogRepo(get_session()).get_audit_logs(
            categories=categories,
            codes=codes,
            text_query=text_query,
            data_query=data_query,
            context_id=context_id,
            created_after=created_after,
            created_before=created_before,
            sort_direction=sort_direction,
            limit=limit,
            offset=offset,
        )

    @require_db_session
    @_create_audit_log
    async def log_app_started(self, app_version: str):
        yield AuditLogCode.APP_STARTED
        yield "Saberr is starting"
        yield {"app_version": app_version}

    @require_db_session
    @_create_audit_log
    async def log_app_exiting(self):
        yield AuditLogCode.APP_EXITED
        yield "Saberr is exiting"
        yield {}

    @_create_audit_log
    async def log_login_succeeded(self, ip_address: str, browser: str, country: str | None):
        yield AuditLogCode.LOGIN_SUCCEEDED
        yield "User login succeeded"
        yield {
            "ip_address": ip_address,
            "browser": browser,
            "country": country
        }

    @_create_audit_log
    async def log_login_failed(self, ip_address: str, username: str, browser: str, country: str | None):
        yield AuditLogCode.LOGIN_FAILED
        yield "User login failed"
        yield {
            "ip_address": ip_address,
            "browser": browser,
            "country": country,
            "username": username
        }

    @_create_audit_log
    async def log_setting_changed(self, setting_name: str, old_value: Any, new_value: Any):
        yield AuditLogCode.SETTING_CHANGED
        if isinstance(old_value, bool):
            old_value_str = "enabled" if old_value else "disabled"
        elif isinstance(old_value, Enum):
            old_value = old_value.value
            old_value_str = old_value
        elif old_value is None:
            old_value_str = "empty"
        else:
            old_value_str = str(old_value)
        if isinstance(new_value, bool):
            new_value_str = "enabled" if new_value else "disabled"
        elif isinstance(new_value, Enum):
            new_value = new_value.value
            new_value_str = new_value
        elif new_value is None:
            new_value_str = "empty"
        else:
            new_value_str = str(new_value)
        yield f"User changed setting '{setting_name}' from '{old_value_str}' to '{new_value_str}'"
        yield {
            "setting_name": setting_name,
            "old_value": old_value,
            "new_value": new_value
        }

    @_create_audit_log
    async def log_torrent_selected_action(self,
                                          db_torrents: list[Torrent],
                                          download_directory_path: str | None,
                                          manually_selected: bool = False,):
        yield AuditLogCode.TORRENT_SELECTED if not manually_selected else AuditLogCode.TORRENT_MANUALLY_SELECTED
        nyaa_torrent = NyaaItem.from_xml_string(db_torrents[0].rss_xml)
        torrent_title = nyaa_torrent.title
        preferred_title = db_torrents[0].tracked_anime_episode.tracked_anime.preferred_title
        episode = self._get_tracked_anime_episodes_descriptor(tracked_anime_episodes=[torrent.tracked_anime_episode
                                                                                      for torrent in db_torrents],
                                                              episode_part=db_torrents[0].episode_part,
                                                              episode_part_ceiling=db_torrents[0].episode_part_ceiling)
        data = {
            "magnet_hash": nyaa_torrent.magnet_hash,
            "torrent_description": nyaa_torrent.clean_description,
            "torrent_title": torrent_title,
            "destination_path": download_directory_path,
            "anime_title": {
                "native": db_torrents[0].tracked_anime_episode.tracked_anime.native_title,
                "romaji": db_torrents[0].tracked_anime_episode.tracked_anime.romaji_title,
                "english": db_torrents[0].tracked_anime_episode.tracked_anime.english_title,
            },
            "episode_numbers": [db_torrent.tracked_anime_episode.episode_number for db_torrent in db_torrents],
            "tvdb_episode_numbers": [
                tvdb_episode_number
                for db_torrent in db_torrents
                for tvdb_episode_number in db_torrent.tracked_anime_episode.tvdb_episode_numbers
            ],
            "tvdb_season_number": db_torrents[0].tracked_anime_episode.tvdb_season_number
        }
        yield f"Selected Torrent '{torrent_title}' for download for anime {preferred_title} - {episode}"
        yield data | {"manually_selected": manually_selected}

    @_create_audit_log
    async def log_torrent_discarded_action(self,
                                           db_torrent: Torrent,
                                           tracked_anime_episode: TrackedAnimeEpisode,
                                           tracked_anime: TrackedAnime):
        yield AuditLogCode.TORRENT_DISCARDED
        nyaa_torrent = NyaaItem.from_xml_string(db_torrent.rss_xml)
        torrent_title = nyaa_torrent.title
        episode = self._get_tracked_anime_episodes_descriptor(tracked_anime_episodes=[tracked_anime_episode],
                                                              episode_part=db_torrent.episode_part,
                                                              episode_part_ceiling=db_torrent.episode_part_ceiling)
        data = {
            "magnet_hash": nyaa_torrent.magnet_hash,
            "torrent_description": nyaa_torrent.clean_description,
            "torrent_title": torrent_title,
            "anime_title": {
                "native": tracked_anime.native_title,
                "romaji": tracked_anime.romaji_title,
                "english": tracked_anime.english_title,
            },
            "episode_number": tracked_anime_episode.episode_number,
            "tvdb_episode_numbers": [
                tvdb_episode_number
                for tvdb_episode_number in tracked_anime_episode.tvdb_episode_numbers
            ],
            "tvdb_season_number": tracked_anime_episode.tvdb_season_number
        }
        yield (f"Discarded Torrent '{torrent_title}' for anime {tracked_anime.preferred_title} "
               f"- {episode}")
        yield data

    @_create_audit_log
    async def log_torrent_processing_action(self, code: AuditLogCode,
                                            torrent_download: TorrentDownload,
                                            db_torrents: list[Torrent]):
        yield code
        nyaa_torrent = NyaaItem.from_xml_string(db_torrents[0].rss_xml)
        torrent_title = nyaa_torrent.title
        preferred_title = db_torrents[0].tracked_anime_episode.tracked_anime.preferred_title
        episode = self._get_tracked_anime_episodes_descriptor(tracked_anime_episodes=[db_torrent.tracked_anime_episode
                                                                                      for db_torrent in db_torrents],
                                                              episode_part=db_torrents[0].episode_part,
                                                              episode_part_ceiling=db_torrents[0].episode_part_ceiling)
        data = {
            "torrent_download_id": torrent_download.id,
            "magnet_hash": nyaa_torrent.magnet_hash,
            "torrent_description": nyaa_torrent.clean_description,
            "torrent_title": torrent_title,
            "anime_title": {
                "native": db_torrents[0].tracked_anime_episode.tracked_anime.native_title,
                "romaji": db_torrents[0].tracked_anime_episode.tracked_anime.romaji_title,
                "english": db_torrents[0].tracked_anime_episode.tracked_anime.english_title,
            },
            "episode_numbers": [db_torrent.tracked_anime_episode.episode_number for db_torrent in db_torrents],
            "tvdb_episode_numbers": [
                tvdb_episode_number
                for db_torrent in db_torrents
                for tvdb_episode_number in db_torrent.tracked_anime_episode.tvdb_episode_numbers
            ],
            "tvdb_season_number": db_torrents[0].tracked_anime_episode.tvdb_season_number,
            "download_directory_path": torrent_download.download_directory_path,
            "destination_path": torrent_download.destination_path
        }
        match code:
            case AuditLogCode.TORRENT_DOWNLOAD_STARTED:
                yield (f"Started download of Torrent '{torrent_title}' for anime {preferred_title} "
                       f"- {episode}")
                yield data
            case AuditLogCode.TORRENT_DOWNLOAD_FINISHED:
                yield (f"Finished download of Torrent '{torrent_title}' for anime {preferred_title} "
                       f"- {episode}")
                yield data
            case AuditLogCode.TORRENT_DOWNLOAD_FAILED:
                yield (f"Failed download of Torrent '{torrent_title}' for anime {preferred_title} "
                       f"- {episode} due to {torrent_download.status_details}")
                yield data | {"failure_reason": torrent_download.status_details}
            case AuditLogCode.TORRENT_DOWNLOAD_DISCARDED:
                yield (f"Discarded download of Torrent '{torrent_title}' for anime {preferred_title} "
                       f"- {episode} due to {torrent_download.status_details}")
                yield data
            case AuditLogCode.TORRENT_DOWNLOAD_DELETED:
                yield (f"Download of Torrent found deleted on qBit: '{torrent_title}' for anime {preferred_title} "
                       f"- {episode} due to {torrent_download.status_details}")
                yield data | {"failure_reason": torrent_download.status_details}
            case AuditLogCode.TORRENT_PROCESSING_STARTED:
                yield (f"Started processing of Torrent '{torrent_title}' for anime {preferred_title} "
                       f"- {episode}")
                yield data
            case AuditLogCode.TORRENT_PROCESSING_FINISHED:
                yield (f"Finished processing of Torrent '{torrent_title}' for anime {preferred_title} "
                       f"- {episode}")
                yield data
            case AuditLogCode.TORRENT_PROCESSING_FAILED:
                yield (f"Failed processing of Torrent '{torrent_title}' for anime {preferred_title} "
                       f"- {episode} due to {torrent_download.status_details}")
                yield data | {"failure_reason": torrent_download.status_details}
            case _:
                raise

    @_create_audit_log
    async def log_tracked_anime_added_or_removed(self,
                                                 code: AuditLogCode,
                                                 tracked_anime: TrackedAnime,
                                                 profile: TrackedAnimeProfile,
                                                 release_groups_preferences: list[TrackedAnimeReleaseGroupPreferences]):
        yield code
        data = {
            "tracked_anime_id": tracked_anime.id,
            "anilist_id": tracked_anime.anilist_id,
            "anime_title": {
                "native": tracked_anime.native_title,
                "romaji": tracked_anime.romaji_title,
                "english": tracked_anime.english_title,
            },
            "tvdb_structure_enabled": tracked_anime.tvdb_structure_enabled,
            "tvdb_season_type": tracked_anime.tvdb_season_type.value,
            "show_parent_directory": tracked_anime.show_parent_directory,
            "show_folder_name": tracked_anime.show_folder_name,
            "release_groups": [{'name': rgp.release_group,
                                'override_match_against': rgp.override_match_against,
                                'episode_number_offset': rgp.episode_number_offset}
                               for rgp in release_groups_preferences
                               if rgp.release_group in profile.preferred_release_groups]
        }
        match code:
            case AuditLogCode.TRACKED_ANIME_ADDED:
                yield f"Added tracked anime '{tracked_anime.preferred_title}'"
                yield data
            case AuditLogCode.TRACKED_ANIME_REMOVED:
                yield f"Removed tracked anime '{tracked_anime.preferred_title}'"
                yield data
            case _:
                raise

    @_create_audit_log
    async def log_tracked_anime_settings_change(self, tracked_anime: TrackedAnime,
                                                update_data: dict[str, dict[str, Any]]):
        yield AuditLogCode.TRACKED_ANIME_UPDATED
        yield f"Updated settings for tracked anime '{tracked_anime.preferred_title}'"
        yield {
            "tracked_anime_id": tracked_anime.id,
            "anilist_id": tracked_anime.anilist_id,
            "anime_title": {
                "native": tracked_anime.native_title,
                "romaji": tracked_anime.romaji_title,
                "english": tracked_anime.english_title,
            },
            "updated_fields": update_data
        }

    @_create_audit_log
    async def log_tracked_anime_archived(self, tracked_anime: TrackedAnime):
        yield AuditLogCode.TRACKED_ANIME_UPDATED
        yield f"Tracked anime '{tracked_anime.preferred_title}' archived"
        yield {
            "tracked_anime_id": tracked_anime.id,
            "anilist_id": tracked_anime.anilist_id,
            "anime_title": {
                "native": tracked_anime.native_title,
                "romaji": tracked_anime.romaji_title,
                "english": tracked_anime.english_title,
            }
        }

    @_create_audit_log
    async def log_user_added_or_removed_anime_from_list(self, code: AuditLogCode, anime_id: int, user_data: dict):
        from components.service_components.anilist_component import AnilistComponent
        yield code
        anime = (await AnilistComponent().get_anime_records(anilist_anime_ids=[anime_id]))[0]
        data = {
            "anime_id": anime_id,
            "anime_title": anime.preferred_title,
            "user_data": user_data
        }
        match code:
            case AuditLogCode.ANILIST_ANIME_ADDED:
                yield f"Added anime '{anime.preferred_title if anime else anime_id}' to user's Anilist anime list"
                yield data
            case AuditLogCode.ANILIST_ANIME_DELETED:
                yield f"Removed anime '{anime.preferred_title if anime else anime_id}' from user's Anilist anime list"
                yield data
            case _:
                raise

    @_create_audit_log
    async def log_user_batch_added_or_removed_anime_from_list(self, code: AuditLogCode,
                                                              anime_ids: list[int],
                                                              user_data: dict | None = None,):
        from components.service_components.anilist_component import AnilistComponent
        yield code
        anime = await AnilistComponent().get_anime_records(anilist_anime_ids=anime_ids)
        data = {
            "anime_ids": anime_ids,
            "anime_titles": [anime.preferred_title for anime in anime]
        }
        match code:
            case AuditLogCode.BATCH_ANILIST_ANIME_ADDED:
                yield f"Added {len(anime_ids)} anime to user's Anilist anime list"
                yield data | {"user_data": user_data}
            case AuditLogCode.BATCH_ANILIST_ANIME_DELETED:
                yield f"Removed {len(anime_ids)} anime from user's Anilist anime list"
                yield data
            case _:
                raise

    @_create_audit_log
    async def log_user_updated_anime_list_entry(self, anime_id: int, updated_data: dict):
        from components.service_components.anilist_component import AnilistComponent
        yield AuditLogCode.ANILIST_ANIME_UPDATED
        anime = (await AnilistComponent().get_anime_records(anilist_anime_ids=[anime_id]))[0]
        yield f"Updated anime list entry for anime '{anime.preferred_title}'"
        yield {
            "anime_id": anime_id,
            "anime_title": anime.preferred_title,
            "changes": updated_data
        }

    @_create_audit_log
    async def log_batch_user_updated_anime_list_entry(self, anime_ids: list[int], updated_data: dict):
        from components.service_components.anilist_component import AnilistComponent
        yield AuditLogCode.BATCH_ANILIST_ANIME_UPDATED
        anime = await AnilistComponent().get_anime_records(anilist_anime_ids=anime_ids)
        yield f"Updated anime list entry for {len(anime_ids)} anime"
        yield {
            "anime_ids": anime_ids,
            "anime_titles": [anime.preferred_title for anime in anime],
            "changes": updated_data
        }

    @_create_audit_log
    async def log_user_anime_list_refreshed(self):
        yield AuditLogCode.ANILIST_LIST_REFRESHED
        yield "Refreshed cached user's Anilist anime list"
        yield {}

    @_create_audit_log
    async def log_service_changed_status(self, code: AuditLogCode, current_status: 'ServiceStatus'):
        yield code
        yield f"Service '{current_status.name}' changed status to {'UP' if current_status.healthy else 'DOWN'}"
        yield current_status.to_dict(compact=True)

    @_create_audit_log
    async def log_anime_relations_refreshed(self):
        yield AuditLogCode.ANIME_RELATIONS_REFRESHED
        yield "Refreshed anime relations data"
        yield {}

    @_create_audit_log
    async def log_mapping_override_added_or_removed(self, code: AuditLogCode,
                                                    anilist_id: int, anilist_from_episode: int,
                                                    anilist_to_episode: int | None, tvdb_series_id: int,
                                                    tvdb_season_number: int, tvdb_from_episode: int,
                                                    tvdb_to_episode: int | None, granularity: int,
                                                    mode: MappingOverrideMode, anilist_title: str | None,
                                                    tvdb_series_title: str | None):
        yield code
        action = "Added" if code == AuditLogCode.MAPPING_OVERRIDE_ADDED else "Removed"
        yield (f"{action} mapping override for Anilist {f'\'{anilist_title}\'' if anilist_title else f'#{anilist_id}'} "
               f"(Ep{anilist_from_episode}-{'Ep' + str(anilist_to_episode) if anilist_to_episode else ''}) "
               f"to TVDB series {f'\'{tvdb_series_title}\'' if tvdb_series_title else f'#{tvdb_series_id}'} "
               f"(S{tvdb_season_number}E{tvdb_from_episode}-{'E' + str(tvdb_to_episode) if tvdb_to_episode else ''}) "
               f"with granularity {granularity} and mode {mode.value}")
        yield {
            "anilist_id": anilist_id,
            "anilist_from_episode": anilist_from_episode,
            "anilist_to_episode": anilist_to_episode,
            "tvdb_series_id": tvdb_series_id,
            "tvdb_season_number": tvdb_season_number,
            "tvdb_from_episode": tvdb_from_episode,
            "tvdb_to_episode": tvdb_to_episode,
            "granularity": granularity,
            "mode": mode.value,
            "anilist_title": anilist_title,
            "tvdb_series_title": tvdb_series_title,
        }

    @_create_audit_log
    async def log_mapping_override_updated(self, updated_data: dict[str, dict], anilist_id: int | None,
                                           tvdb_series_id: int | None, anilist_title: str | None,
                                           tvdb_series_title: str | None):
        yield AuditLogCode.MAPPING_OVERRIDE_UPDATED
        if anilist_id:
            text = (f"Updated mapping override for Anilist "
                    f"{f'\'{anilist_title}\'' if anilist_title else f'#{anilist_id}'}")
        elif tvdb_series_id:
            text = (f"Updated mapping override for TVDB series "
                    f"{f'\'{tvdb_series_title}\'' if tvdb_series_title else f'#{tvdb_series_id}'}")
        else:
            text = "Updated mapping override"
        yield text
        yield {
            "anilist_id": anilist_id,
            "tvdb_series_id": tvdb_series_id,
            "anilist_title": anilist_title,
            "tvdb_series_title": tvdb_series_title,
            "updated_fields": updated_data
        }

    @staticmethod
    def _get_tracked_anime_episodes_descriptor(tracked_anime_episodes: list[TrackedAnimeEpisode],
                                               episode_part: int,
                                               episode_part_ceiling: int) -> str:
        if len(tracked_anime_episodes) == 1:
            episode = f"Episode #{tracked_anime_episodes[0].episode_number}"
            if episode_part:
                episode += f" Part {episode_part}/{episode_part_ceiling}"
        else:
            episodes = ', '.join([f"#{episode.episode_number}" for episode in tracked_anime_episodes])
            episode = f"Episodes {episodes}"
        tvdb_episode_numbers = [tvdb_episode_number 
                                for tracked_anime_episode in tracked_anime_episodes 
                                for tvdb_episode_number in tracked_anime_episode.tvdb_episode_numbers]
        if tvdb_episode_numbers:
            episode += f" (S{tracked_anime_episodes[0].tvdb_season_number}E{', '.join(map(str, tvdb_episode_numbers))})"
        return episode
