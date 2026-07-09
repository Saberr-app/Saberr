from sqlalchemy import select, update, delete
from sqlalchemy.orm import joinedload, load_only

from constants import ReleaseCriteriaProperty, Encoding, Resolution, VideoSource
from dto.orm_models import TrackedAnimeProfile
from repositories import BaseRepo


class TrackedAnimeProfileRepo(BaseRepo):

    # noinspection PyTypeChecker
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

        profile = TrackedAnimeProfile(
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
        self._session.add(profile)
        await self._session.flush()
        return profile

    async def get_tracked_anime_profile(self, tracked_anime_profile_id: int,
                                        load_tracked_anime_list: bool = False,
                                        only: tuple[str] = ()) -> TrackedAnimeProfile:
        query = select(TrackedAnimeProfile).where(
            TrackedAnimeProfile.id == tracked_anime_profile_id,
        )
        if load_tracked_anime_list:
            query = query.options(
                joinedload(TrackedAnimeProfile.tracked_anime_list)
            )
        if only:
            query = query.options(load_only(*(getattr(TrackedAnimeProfile, column) for column in only)))
        return (await self._session.execute(query)).unique().scalar_one_or_none()

    async def update_tracked_anime_profile(self, profile_id: int, **update_data):
        if not update_data:
            return
        await self._session.execute(
            update(TrackedAnimeProfile).where(TrackedAnimeProfile.id == profile_id).values(**update_data)
        )
        await self._session.flush()

    async def delete_tracked_anime_profile(self, profile_id: int):
        await self._session.execute(
            delete(TrackedAnimeProfile).where(TrackedAnimeProfile.id == profile_id)
        )
