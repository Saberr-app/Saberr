from common.db import get_session
from common.exceptions import ObjectNotFoundException
from components.operational_components import BaseOperationalComponent
from constants import ReleaseCriteriaProperty, Encoding, Resolution, VideoSource
from dto.orm_models import TrackedAnimeProfile
from system import UNSET
from app_state import global_status
from repositories.tracked_anime_repositories.tracked_anime_profile_repo import TrackedAnimeProfileRepo


class TrackedAnimeProfileComponent(BaseOperationalComponent):

    # noinspection PyMethodMayBeStatic
    async def create_tracked_anime_profile(self,
                                           preferred_release_groups: list[str],
                                           preferred_encodings: list[Encoding],
                                           preferred_resolutions: list[Resolution],
                                           preferred_language_codes: list[str],
                                           preferred_sources: list[VideoSource],
                                           language_codes_restricted: bool,
                                           sources_restricted: bool,
                                           accept_release_upgrades: bool,
                                           priorities_sorted: list[ReleaseCriteriaProperty]) -> TrackedAnimeProfile:
        return await TrackedAnimeProfileRepo(get_session()).create_tracked_anime_profile(
            preferred_release_groups=preferred_release_groups,
            preferred_encodings=preferred_encodings,
            preferred_resolutions=preferred_resolutions,
            preferred_language_codes=preferred_language_codes,
            preferred_sources=preferred_sources,
            language_codes_restricted=language_codes_restricted,
            sources_restricted=sources_restricted,
            accept_release_upgrades=accept_release_upgrades,
            priorities_sorted=priorities_sorted
        )

    # noinspection PyMethodMayBeStatic
    async def get_default_tracked_anime_profile(self, only: tuple[str] = ()) -> TrackedAnimeProfile:
        return await TrackedAnimeProfileRepo(get_session()).get_tracked_anime_profile(tracked_anime_profile_id=1,
                                                                                      only=only)

    async def update_tracked_anime_profile(self,
                                           profile_id: int,
                                           preferred_release_groups: list[str] = UNSET,
                                           preferred_encodings: list[Encoding] = UNSET,
                                           preferred_resolutions: list[Resolution] = UNSET,
                                           preferred_language_codes: list[str] = UNSET,
                                           preferred_sources: list[VideoSource] = UNSET,
                                           language_codes_restricted: bool = UNSET,
                                           sources_restricted: bool = UNSET,
                                           accept_release_upgrades: bool = UNSET,
                                           priorities_sorted: list[ReleaseCriteriaProperty] = UNSET):
        tracked_anime_profile = await TrackedAnimeProfileRepo(get_session()).get_tracked_anime_profile(
            tracked_anime_profile_id=profile_id, load_tracked_anime_list=True
        )
        if not tracked_anime_profile:
            raise ObjectNotFoundException("Profile not found")

        update_data = {}
        updated_data = {}  # {name: {old:_, new:_}}

        if preferred_release_groups is not UNSET \
                and tracked_anime_profile.preferred_release_groups != preferred_release_groups:
            update_data["preferred_release_groups"] = preferred_release_groups
            updated_data["Preferred release groups"] = {"old": tracked_anime_profile.preferred_release_groups,
                                                        "new": preferred_release_groups}
        old_preferred_encodings = [encoding.value for encoding  # noqa
                                   in tracked_anime_profile.preferred_encodings]
        if preferred_encodings is not UNSET \
                and old_preferred_encodings != [encoding.value for encoding in preferred_encodings]:
            update_data["preferred_encodings"] = preferred_encodings
            updated_data["Preferred encodings"] = {"old": old_preferred_encodings,
                                                   "new": [encoding.value for encoding in preferred_encodings]}
        old_preferred_resolutions = [resolution.value for resolution  # noqa
                                     in tracked_anime_profile.preferred_resolutions]
        if preferred_resolutions is not UNSET \
                and old_preferred_resolutions != [resolution.value for resolution in preferred_resolutions]:
            update_data["preferred_resolutions"] = preferred_resolutions
            updated_data["Preferred resolutions"] = {"old": old_preferred_resolutions,
                                                     "new": [resolution.value for resolution in preferred_resolutions]}
        if preferred_language_codes is not UNSET \
                and tracked_anime_profile.preferred_language_codes != preferred_language_codes:
            update_data["preferred_language_codes"] = preferred_language_codes
            updated_data["Preferred language codes"] = {"old": tracked_anime_profile.preferred_language_codes,
                                                        "new": preferred_language_codes}
        old_preferred_sources = [source.value for source  # noqa
                                 in tracked_anime_profile.preferred_sources]
        if preferred_sources is not UNSET \
                and old_preferred_sources != [source.value for source in preferred_sources]:
            update_data["preferred_sources"] = preferred_sources
            updated_data["Preferred sources"] = {"old": old_preferred_sources,
                                                 "new": [source.value for source in preferred_sources]}
        if language_codes_restricted is not UNSET \
                and tracked_anime_profile.language_codes_restricted != language_codes_restricted:
            update_data["language_codes_restricted"] = language_codes_restricted
            updated_data["Language codes restricted"] = {"old": tracked_anime_profile.language_codes_restricted,
                                                         "new": language_codes_restricted}
        if sources_restricted is not UNSET and tracked_anime_profile.sources_restricted != sources_restricted:
            update_data["sources_restricted"] = sources_restricted
            updated_data["Sources restricted"] = {"old": tracked_anime_profile.sources_restricted,
                                                  "new": sources_restricted}
        if accept_release_upgrades is not UNSET \
                and tracked_anime_profile.accept_release_upgrades != accept_release_upgrades:
            update_data["accept_release_upgrades"] = accept_release_upgrades
            updated_data["Accept release upgrades"] = {"old": tracked_anime_profile.accept_release_upgrades,
                                                       "new": accept_release_upgrades}
        old_priorities_sorted = [priority.value for priority in tracked_anime_profile.priorities_sorted]
        if priorities_sorted is not UNSET \
                and old_priorities_sorted != [priority.value for priority in priorities_sorted]:
            update_data["priorities_sorted"] = priorities_sorted
            updated_data["Priorities sorted"] = {"old": old_priorities_sorted,
                                                 "new": [priority.value for priority in priorities_sorted]}

        if not update_data:
            return

        await TrackedAnimeProfileRepo(get_session()).update_tracked_anime_profile(profile_id=profile_id,
                                                                                  **update_data)

        if profile_id == 1:
            for setting_name, change in updated_data.items():
                await self._audit_log_component.log_setting_changed(setting_name=f"Default {setting_name.lower()}",
                                                                    old_value=change["old"],
                                                                    new_value=change["new"])
            global_status.settings_updated()
        elif tracked_anime_profile.tracked_anime_list:
            await self._audit_log_component.log_tracked_anime_settings_change(
                tracked_anime=tracked_anime_profile.tracked_anime_list[0],
                update_data=updated_data
            )
            global_status.tracked_anime_updated()
