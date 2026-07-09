from sqlalchemy import select, update, delete
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import joinedload

from dto.orm_models import TrackedAnimeReleaseGroupPreferences
from repositories import BaseRepo


class TrackedAnimeReleaseGroupPreferencesRepo(BaseRepo):

    # noinspection PyTypeChecker
    async def create_tracked_anime_release_group_preferences(self,
                                                             tracked_anime_id: int,
                                                             release_group: str,
                                                             episode_number_offset: int,
                                                             override_match_against: str | None = None
                                                             ) -> TrackedAnimeReleaseGroupPreferences:
        preferences = TrackedAnimeReleaseGroupPreferences(
            tracked_anime_id=tracked_anime_id,
            release_group=release_group,
            episode_number_offset=episode_number_offset,
            override_match_against=override_match_against
        )
        self._session.add(preferences)
        await self._session.flush()
        return preferences

    async def get_tracked_anime_release_group_preferences(self,
                                                          tracked_anime_id: int,
                                                          release_group: str,
                                                          load_relations: bool = False
                                                          ) -> TrackedAnimeReleaseGroupPreferences | None:
        query = select(TrackedAnimeReleaseGroupPreferences).where(
            TrackedAnimeReleaseGroupPreferences.tracked_anime_id == tracked_anime_id,
            TrackedAnimeReleaseGroupPreferences.release_group == release_group
        )
        if load_relations:
            query = query.options(joinedload(TrackedAnimeReleaseGroupPreferences.tracked_anime))
        return (await self._session.execute(query)).unique().scalar_one_or_none()

    async def update_tracked_anime_release_group_preferences(self, preferences_id: int, **update_data):
        if not update_data:
            return
        await self._session.execute(
            update(TrackedAnimeReleaseGroupPreferences).where(
                TrackedAnimeReleaseGroupPreferences.id == preferences_id
            ).values(**update_data)
        )
        await self._session.flush()

    async def upsert_tracked_anime_release_group_preferences(self, tracked_anime_id: int,
                                                             release_group: str, update_data: dict):
        if not update_data:
            return
        insert_stmt = insert(TrackedAnimeReleaseGroupPreferences).values(
            tracked_anime_id=tracked_anime_id,
            release_group=release_group,
            **update_data
        )
        await self._session.execute(
            insert_stmt.on_duplicate_key_update(**update_data)
        )
        await self._session.flush()

    async def delete_tracked_anime_release_group_preferences(self, preferences_id: int):
        await self._session.execute(
            delete(TrackedAnimeReleaseGroupPreferences).where(
                TrackedAnimeReleaseGroupPreferences.id == preferences_id
            )
        )
