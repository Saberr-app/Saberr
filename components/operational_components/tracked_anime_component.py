import re
from typing import Iterable

from common.db import get_session
from common.decorators import require_db_session
from common.exceptions import InvalidReleaseGroupException, ObjectNotFoundException
from components.operational_components import BaseOperationalComponent
from components.operational_components.tracked_anime_profile_component import TrackedAnimeProfileComponent
from config import config
from constants import TVDBSeasonType, TrackedAnimeStatus, AuditLogCode
from dto.anilist import AnilistAnime
from dto.orm_models import TrackedAnime, TrackedAnimeReleaseGroupPreferences
from system import UNSET
from app_state import global_status
from repositories.tracked_anime_repositories.tracked_anime_processing_settings_repo import \
    TrackedAnimeProcessingSettingsRepo
from repositories.tracked_anime_repositories.tracked_anime_profile_repo import TrackedAnimeProfileRepo
from repositories.tracked_anime_repositories.tracked_anime_release_group_preferences_repo import \
    TrackedAnimeReleaseGroupPreferencesRepo
from repositories.tracked_anime_repositories.tracked_anime_repo import TrackedAnimeRepo


class TrackedAnimeComponent(BaseOperationalComponent):

    async def create_tracked_anime(self,
                                   anilist_anime: AnilistAnime,
                                   from_episode: int,
                                   tvdb_structure_enabled: bool,
                                   tvdb_season_type: TVDBSeasonType,
                                   show_parent_directory: str,
                                   show_folder_name: str,
                                   episode_number_padding: int,
                                   season_number_padding: int,
                                   season_directory_number_padding: int,
                                   season_directory_name_format: str,
                                   raw_episode_file_name_format: str,
                                   episode_file_name_format: str,
                                   titleless_episode_file_name_format: str,
                                   release_group_overriding_title_map: dict[str, str],
                                   release_group_overriding_offset_map: dict[str, int],
                                   release_profile=None) -> TrackedAnime:
        if release_profile is not None:
            if invalid_releases_groups := (set(release_profile.preferred_release_groups)
                                           - config.release_groups_map.keys()):
                raise InvalidReleaseGroupException(f"Invalid release groups: {', '.join(invalid_releases_groups)}.")
            tracked_anime_profile = await TrackedAnimeProfileComponent().create_tracked_anime_profile(
                preferred_release_groups=release_profile.preferred_release_groups,
                preferred_encodings=release_profile.preferred_encodings,
                preferred_resolutions=release_profile.preferred_resolutions,
                preferred_language_codes=release_profile.preferred_language_codes,
                preferred_sources=release_profile.preferred_sources,
                language_codes_restricted=release_profile.language_codes_restricted,
                sources_restricted=release_profile.sources_restricted,
                accept_release_upgrades=release_profile.accept_release_upgrades,
                priorities_sorted=release_profile.priorities_sorted,
            )
        else:
            tracked_anime_profile = await TrackedAnimeProfileComponent().get_default_tracked_anime_profile()

        tracked_anime = await TrackedAnimeRepo(get_session()).create_tracked_anime(
            tracked_anime_profile_id=tracked_anime_profile.id,
            romaji_title=anilist_anime.romaji_title,
            native_title=anilist_anime.native_title,
            english_title=anilist_anime.english_title,
            anilist_id=anilist_anime.id,
            status=TrackedAnimeStatus.ACTIVE,
            from_episode=from_episode,
            tvdb_structure_enabled=tvdb_structure_enabled,
            tvdb_season_type=tvdb_season_type,
            show_parent_directory=show_parent_directory,
            show_folder_name=show_folder_name
        )
        await TrackedAnimeProcessingSettingsRepo(get_session()).create_tracked_anime_processing_settings(
            tracked_anime_id=tracked_anime.id,
            episode_number_padding=episode_number_padding,
            season_number_padding=season_number_padding,
            season_directory_number_padding=season_directory_number_padding,
            season_directory_name_format=season_directory_name_format,
            raw_episode_file_name_format=raw_episode_file_name_format,
            episode_file_name_format=episode_file_name_format,
            titleless_episode_file_name_format=titleless_episode_file_name_format,
        )
        release_groups_preferences = []
        for release_group_name in release_group_overriding_title_map.keys():
            rgp = await TrackedAnimeReleaseGroupPreferencesRepo(get_session()) \
                .create_tracked_anime_release_group_preferences(
                tracked_anime_id=tracked_anime.id,
                release_group=release_group_name,
                episode_number_offset=release_group_overriding_offset_map.get(release_group_name, 0),
                override_match_against=self._normalize_overriding_title(release_group_overriding_title_map.get(
                    release_group_name, None
                )),
            )
            release_groups_preferences.append(rgp)
        await self._audit_log_component.log_tracked_anime_added_or_removed(
            code=AuditLogCode.TRACKED_ANIME_ADDED,
            tracked_anime=tracked_anime,
            profile=tracked_anime_profile,
            release_groups_preferences=release_groups_preferences
        )
        global_status.tracked_anime_updated()
        return tracked_anime

    # noinspection PyMethodMayBeStatic
    async def get_tracked_anime(self, anilist_id: int,
                                load_relations: bool = True) -> TrackedAnime | None:
        return await TrackedAnimeRepo(get_session()).get_tracked_anime(anilist_id=anilist_id,
                                                                       load_relations=load_relations)

    # noinspection PyMethodMayBeStatic
    async def get_tracked_anime_by_id(self, tracked_anime_id: int,
                                      load_relations: bool = True) -> TrackedAnime | None:
        return await TrackedAnimeRepo(get_session()).get_tracked_anime(
            tracked_anime_id=tracked_anime_id, load_relations=load_relations
        )

    # noinspection PyMethodMayBeStatic
    async def get_all_tracked_anime(self, statuses: list[TrackedAnimeStatus] = None,
                                    anilist_ids: Iterable[int] | None = None,
                                    load_relations: bool = True) -> list[TrackedAnime]:
        if statuses is None:
            statuses = [TrackedAnimeStatus.ACTIVE]
        return await TrackedAnimeRepo(get_session()).get_all_tracked_anime(anilist_ids=anilist_ids,
                                                                           statuses=statuses,
                                                                           load_relations=load_relations)

    # noinspection PyMethodMayBeStatic
    async def get_tracked_anime_by_anilist_ids(self,
                                               anilist_ids: Iterable[int],
                                               load_relations: bool = True) -> list[TrackedAnime]:
        return await TrackedAnimeRepo(get_session()).get_tracked_anime_list(anilist_ids=anilist_ids,
                                                                            load_relations=load_relations)

    # noinspection PyMethodMayBeStatic
    async def get_tracked_anime_release_group_overrides_map(
            self,
            title_release_group_pairs: Iterable[tuple[str, str]]
    ) -> dict[tuple[str, str], TrackedAnimeReleaseGroupPreferences]:
        preferences = await TrackedAnimeRepo(get_session()).get_release_group_preferences_for_overriding_titles(
            title_release_group_pairs=title_release_group_pairs
        )
        overrides_map = {}
        for preference in preferences:
            key = (preference.override_match_against, preference.release_group)
            if key not in overrides_map:
                overrides_map[key] = preference
        return overrides_map

    async def update_tracked_anime(self, tracked_anime_id: int,
                                   set_to_active: bool = UNSET,
                                   from_episode: int = UNSET,
                                   tvdb_structure_enabled: bool = UNSET,
                                   tvdb_season_type: TVDBSeasonType = UNSET,
                                   show_parent_directory: str = UNSET,
                                   show_folder_name: str = UNSET,
                                   episode_number_padding: int = UNSET,
                                   season_number_padding: int = UNSET,
                                   season_directory_number_padding: int = UNSET,
                                   season_directory_name_format: str = UNSET,
                                   raw_episode_file_name_format: str = UNSET,
                                   episode_file_name_format: str = UNSET,
                                   titleless_episode_file_name_format: str = UNSET,
                                   release_group_overriding_title_map: dict[str, str] = UNSET,
                                   release_group_overriding_offset_map: dict[str, int] = UNSET,
                                   release_profile=UNSET):
        from components.operational_components.tracked_anime_profile_component import \
            TrackedAnimeProfileComponent
        tracked_anime = await TrackedAnimeRepo(get_session()).get_tracked_anime(tracked_anime_id=tracked_anime_id,
                                                                                load_relations=True)
        if not tracked_anime:
            raise ObjectNotFoundException("Tracked anime not found.")
        tracked_anime_update_data = {}
        profile_to_delete = None
        if release_profile is not UNSET:
            current_profile_id = tracked_anime.tracked_anime_profile_id
            if release_profile is None:
                if current_profile_id != 1:
                    tracked_anime_update_data["tracked_anime_profile_id"] = 1
                    profile_to_delete = current_profile_id
            elif current_profile_id == 1:
                new_profile = await TrackedAnimeProfileComponent().create_tracked_anime_profile(
                    preferred_release_groups=release_profile.preferred_release_groups,
                    preferred_encodings=release_profile.preferred_encodings,
                    preferred_resolutions=release_profile.preferred_resolutions,
                    preferred_language_codes=release_profile.preferred_language_codes,
                    preferred_sources=release_profile.preferred_sources,
                    language_codes_restricted=release_profile.language_codes_restricted,
                    sources_restricted=release_profile.sources_restricted,
                    accept_release_upgrades=release_profile.accept_release_upgrades,
                    priorities_sorted=release_profile.priorities_sorted,
                )
                tracked_anime_update_data["tracked_anime_profile_id"] = new_profile.id
            else:
                await TrackedAnimeProfileComponent().update_tracked_anime_profile(
                    profile_id=current_profile_id,
                    preferred_release_groups=release_profile.preferred_release_groups,
                    preferred_encodings=release_profile.preferred_encodings,
                    preferred_resolutions=release_profile.preferred_resolutions,
                    preferred_language_codes=release_profile.preferred_language_codes,
                    preferred_sources=release_profile.preferred_sources,
                    language_codes_restricted=release_profile.language_codes_restricted,
                    sources_restricted=release_profile.sources_restricted,
                    accept_release_upgrades=release_profile.accept_release_upgrades,
                    priorities_sorted=release_profile.priorities_sorted,
                )
        tracked_anime_processing_settings_update_data = {}
        updated_data = {}  # {field name : {old:_, new:_}}

        if from_episode is not UNSET and tracked_anime.from_episode != from_episode:
            tracked_anime_update_data["from_episode"] = from_episode
            updated_data["Track from episode"] = {"old": tracked_anime.from_episode,
                                                  "new": from_episode}
        if tvdb_structure_enabled is not UNSET and tracked_anime.tvdb_structure_enabled != tvdb_structure_enabled:
            tracked_anime_update_data["tvdb_structure_enabled"] = tvdb_structure_enabled
            updated_data["TVDB structure enabled"] = {"old": tracked_anime.tvdb_structure_enabled,
                                                      "new": tvdb_structure_enabled}
        if tvdb_season_type is not UNSET and tracked_anime.tvdb_season_type != tvdb_season_type:
            tracked_anime_update_data["tvdb_season_type"] = tvdb_season_type
            updated_data["TVDB season type"] = {"old": tracked_anime.tvdb_season_type.value,
                                                "new": tvdb_season_type.value}
        if show_parent_directory is not UNSET and tracked_anime.show_parent_directory != show_parent_directory:
            tracked_anime_update_data["show_parent_directory"] = show_parent_directory
            updated_data["Show parent directory"] = {"old": tracked_anime.show_parent_directory,
                                                     "new": show_parent_directory}
        if show_folder_name is not UNSET and tracked_anime.show_folder_name != show_folder_name:
            tracked_anime_update_data["show_folder_name"] = show_folder_name
            updated_data["Show folder name"] = {"old": tracked_anime.show_folder_name,
                                                "new": show_folder_name}
        if set_to_active is not UNSET and tracked_anime.status != TrackedAnimeStatus.ACTIVE:
            tracked_anime_update_data["status"] = TrackedAnimeStatus.ACTIVE
            updated_data["Status"] = {"old": tracked_anime.status.value,
                                      "new": TrackedAnimeStatus.ACTIVE.value}

        processing_settings = tracked_anime.processing_settings
        if episode_number_padding is not UNSET and processing_settings.episode_number_padding != episode_number_padding:
            tracked_anime_processing_settings_update_data["episode_number_padding"] = episode_number_padding
            updated_data["Episode number padding"] = {"old": processing_settings.episode_number_padding,
                                                      "new": episode_number_padding}
        if season_number_padding is not UNSET and processing_settings.season_number_padding != season_number_padding:
            tracked_anime_processing_settings_update_data["season_number_padding"] = season_number_padding
            updated_data["Season number padding"] = {"old": processing_settings.season_number_padding,
                                                     "new": season_number_padding}
        if season_directory_number_padding is not UNSET \
                and processing_settings.season_directory_number_padding != season_directory_number_padding:
            tracked_anime_processing_settings_update_data["season_directory_number_padding"] = \
                season_directory_number_padding
            updated_data["Season directory number padding"] = {
                "old": processing_settings.season_directory_number_padding,
                "new": season_directory_number_padding}
        if season_directory_name_format is not UNSET \
                and processing_settings.season_directory_name_format != season_directory_name_format:
            tracked_anime_processing_settings_update_data["season_directory_name_format"] = season_directory_name_format
            updated_data["Season directory name format"] = {"old": processing_settings.season_directory_name_format,
                                                            "new": season_directory_name_format}
        if raw_episode_file_name_format is not UNSET \
                and processing_settings.raw_episode_file_name_format != raw_episode_file_name_format:
            tracked_anime_processing_settings_update_data["raw_episode_file_name_format"] = raw_episode_file_name_format
            updated_data["AniList episode file name format"] = {"old": processing_settings.raw_episode_file_name_format,
                                                                "new": raw_episode_file_name_format}
        if episode_file_name_format is not UNSET \
                and processing_settings.episode_file_name_format != episode_file_name_format:
            tracked_anime_processing_settings_update_data["episode_file_name_format"] = episode_file_name_format
            updated_data["Episode file name format"] = {"old": processing_settings.episode_file_name_format,
                                                        "new": episode_file_name_format}
        if titleless_episode_file_name_format is not UNSET \
                and processing_settings.titleless_episode_file_name_format != titleless_episode_file_name_format:
            tracked_anime_processing_settings_update_data["titleless_episode_file_name_format"] = \
                titleless_episode_file_name_format
            updated_data["Titleless episode file name format"] = {
                "old": processing_settings.titleless_episode_file_name_format,
                "new": titleless_episode_file_name_format}

        if release_profile is not None \
                and (invalid_releases_groups := (set(release_profile.preferred_release_groups)
                                                 - config.release_groups_map.keys())):
            raise InvalidReleaseGroupException(f"Invalid release groups: {', '.join(invalid_releases_groups)}.")
        if release_group_overriding_title_map is not UNSET \
                and (invalid_releases_groups := (set(release_group_overriding_title_map)
                                                 - config.release_groups_map.keys())):
            raise InvalidReleaseGroupException(f"Invalid release groups: {', '.join(invalid_releases_groups)}.")
        if release_group_overriding_offset_map is not UNSET \
                and (invalid_releases_groups := (set(release_group_overriding_offset_map)
                                                 - config.release_groups_map.keys())):
            raise InvalidReleaseGroupException(f"Invalid release groups: {', '.join(invalid_releases_groups)}.")

        # need to clean up this mess, make it so that the received overrides are the source of truth about current RGs
        # overrides, requires FE change
        release_group_preferences_by_name = {rgp.release_group: rgp
                                             for rgp in tracked_anime.release_groups_preferences}
        updated_release_group_names = set()
        if release_group_overriding_title_map is not UNSET:
            updated_release_group_names.update(release_group_overriding_title_map.keys())
        if release_group_overriding_offset_map is not UNSET:
            updated_release_group_names.update(release_group_overriding_offset_map.keys())
        tracked_anime_release_group_preferences_update_data = {
            release_group: {"episode_number_offset": 0, "override_match_against": None}
            for release_group in updated_release_group_names
        }
        for release_group in updated_release_group_names:
            rgp_update_data = {}
            if release_group_overriding_offset_map is not UNSET:
                new_offset = release_group_overriding_offset_map.get(release_group, 0)
                old_offset = release_group_preferences_by_name[release_group].episode_number_offset \
                    if release_group in release_group_preferences_by_name else 0
                if old_offset != new_offset:
                    rgp_update_data["episode_number_offset"] = new_offset
                    updated_data[f"{release_group} -> episode number offset"] = {"old": old_offset,
                                                                                 "new": new_offset}
                else:
                    rgp_update_data["episode_number_offset"] = old_offset
            elif release_group_preferences_by_name.get(release_group):
                rgp_update_data["episode_number_offset"] = \
                    release_group_preferences_by_name[release_group].episode_number_offset
            if release_group_overriding_title_map is not UNSET:
                new_title = self._normalize_overriding_title(
                    release_group_overriding_title_map.get(release_group, None)
                )
                old_title = release_group_preferences_by_name[release_group].override_match_against \
                    if release_group in release_group_preferences_by_name else None
                if old_title != new_title:
                    rgp_update_data["override_match_against"] = new_title
                    updated_data[f"{release_group} -> overriding title"] = {"old": old_title,
                                                                            "new": new_title}
                else:
                    rgp_update_data["override_match_against"] = old_title
            elif release_group_preferences_by_name.get(release_group):
                rgp_update_data["override_match_against"] = \
                    release_group_preferences_by_name[release_group].override_match_against
            if rgp_update_data:
                tracked_anime_release_group_preferences_update_data[release_group] |= rgp_update_data

        if tracked_anime_update_data:
            await TrackedAnimeRepo(get_session()).update_tracked_anime(tracked_anime_id=tracked_anime_id,
                                                                       **tracked_anime_update_data)
        if profile_to_delete is not None:
            await TrackedAnimeProfileRepo(get_session()).delete_tracked_anime_profile(
                profile_id=profile_to_delete
            )
        if tracked_anime_processing_settings_update_data:
            await TrackedAnimeProcessingSettingsRepo(get_session()).update_tracked_anime_processing_settings(
                settings_id=processing_settings.id,
                **tracked_anime_processing_settings_update_data
            )
        for release_group, rgp_update_data in tracked_anime_release_group_preferences_update_data.items():
            await TrackedAnimeReleaseGroupPreferencesRepo(get_session()) \
                .upsert_tracked_anime_release_group_preferences(
                tracked_anime_id=tracked_anime_id,
                release_group=release_group,
                update_data=rgp_update_data
            )

        if updated_data:
            await self._audit_log_component.log_tracked_anime_settings_change(tracked_anime=tracked_anime,
                                                                              update_data=updated_data)
            global_status.tracked_anime_updated()

    async def archive_tracked_anime(self, tracked_anime_ids: list[int] | None = None,
                                    anilist_ids: list[int] | None = None):
        tracked_anime_list = await self._resolve_tracked_anime(tracked_anime_ids, anilist_ids)
        for tracked_anime in tracked_anime_list:
            await TrackedAnimeRepo(get_session()).update_tracked_anime(tracked_anime_id=tracked_anime.id,
                                                                       status=TrackedAnimeStatus.ARCHIVED)
            await self._audit_log_component.log_tracked_anime_archived(tracked_anime=tracked_anime)
        global_status.tracked_anime_updated()

    async def unarchive_tracked_anime(self, tracked_anime_ids: list[int] | None = None,
                                      anilist_ids: list[int] | None = None):
        tracked_anime_list = await self._resolve_tracked_anime(tracked_anime_ids, anilist_ids)
        for tracked_anime in tracked_anime_list:
            await TrackedAnimeRepo(get_session()).update_tracked_anime(tracked_anime_id=tracked_anime.id,
                                                                       status=TrackedAnimeStatus.ACTIVE)
            await self._audit_log_component.log_tracked_anime_settings_change(tracked_anime=tracked_anime,
                                                                              update_data={"Status": {"old": "Archived",
                                                                                                      "new": "Active"}})
        global_status.tracked_anime_updated()

    async def delete_tracked_anime(self, tracked_anime_ids: list[int] | None = None,
                                   anilist_ids: list[int] | None = None):
        tracked_anime_list = await self._resolve_tracked_anime(tracked_anime_ids, anilist_ids)
        for tracked_anime in tracked_anime_list:
            await TrackedAnimeRepo(get_session()).delete_tracked_anime(tracked_anime_id=tracked_anime.id)
            await self._audit_log_component.log_tracked_anime_added_or_removed(
                code=AuditLogCode.TRACKED_ANIME_REMOVED,
                tracked_anime=tracked_anime,
                profile=tracked_anime.profile,
                release_groups_preferences=tracked_anime.release_groups_preferences
            )
        global_status.tracked_anime_updated()

    # noinspection PyMethodMayBeStatic
    async def _resolve_tracked_anime(self, tracked_anime_ids: list[int] | None,
                                     anilist_ids: list[int] | None) -> list[TrackedAnime]:
        if not tracked_anime_ids and not anilist_ids:
            raise ValueError("Either tracked_anime_ids or anilist_ids must be provided")
        tracked_anime_list = await TrackedAnimeRepo(get_session()).get_tracked_anime_list(
            tracked_anime_ids=tracked_anime_ids,
            anilist_ids=anilist_ids if not tracked_anime_ids else None,
            load_relations=True
        )
        if tracked_anime_ids:
            requested, found = set(tracked_anime_ids), {ta.id for ta in tracked_anime_list}
        else:
            requested, found = set(anilist_ids), {ta.anilist_id for ta in tracked_anime_list}
        missing = requested - found
        if missing:
            raise ObjectNotFoundException(f"Tracked anime not found: {sorted(missing)}")
        return tracked_anime_list

    @require_db_session
    async def update_tracked_anime_from_anilist(self, anime_records: list[AnilistAnime]):
        anilist_id_record_map = {anime_record.id: anime_record for anime_record in anime_records}
        tracked_anime_list = await TrackedAnimeRepo(get_session()).get_tracked_anime_list(
            anilist_ids=anilist_id_record_map.keys(),
            load_relations=False
        )
        update_mappings = []
        for tracked_anime in tracked_anime_list:
            anime_record = anilist_id_record_map[tracked_anime.anilist_id]
            if tracked_anime.romaji_title == anime_record.romaji_title \
                    and tracked_anime.native_title == anime_record.native_title \
                    and tracked_anime.english_title == anime_record.english_title:
                continue
            update_mappings.append({
                "id": tracked_anime.id,
                "romaji_title": anime_record.romaji_title,
                "native_title": anime_record.native_title,
                "english_title": anime_record.english_title,
            })
        if update_mappings:
            await TrackedAnimeRepo(get_session()).batch_update_tracked_anime(update_mappings=update_mappings)
            global_status.tracked_anime_updated()

    # noinspection PyMethodMayBeStatic
    async def update_tracked_anime_release_group_overriding_title(self,
                                                                  tracked_anime_id: int,
                                                                  release_group: str,
                                                                  title: str,
                                                                  offset: int):
        rgp_repo = TrackedAnimeReleaseGroupPreferencesRepo(get_session())
        if rgp := await rgp_repo.get_tracked_anime_release_group_preferences(tracked_anime_id=tracked_anime_id,
                                                                             release_group=release_group):
            await rgp_repo.update_tracked_anime_release_group_preferences(
                preferences_id=rgp.id,
                override_match_against=self._normalize_overriding_title(title),
                episode_number_offset=offset
            )
        else:
            await rgp_repo.create_tracked_anime_release_group_preferences(
                tracked_anime_id=tracked_anime_id,
                release_group=release_group,
                override_match_against=self._normalize_overriding_title(title),
                episode_number_offset=offset
            )

    @staticmethod
    def _normalize_overriding_title(title: str | None) -> str | None:
        if not title:
            return None
        return re.sub(r"\bS0*(\d+)\s*$", r"Season \1", title, flags=re.IGNORECASE)
