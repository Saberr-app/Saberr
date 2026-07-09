from typing import Iterable

from sqlalchemy import select, update, delete
from sqlalchemy.orm import joinedload

from constants import TrackedAnimeStatus
from dto.orm_models import TrackedAnimeProcessingSettings, TrackedAnime
from repositories import BaseRepo


class TrackedAnimeProcessingSettingsRepo(BaseRepo):

    # noinspection PyTypeChecker
    async def create_tracked_anime_processing_settings(self,
                                                       tracked_anime_id: int,
                                                       season_directory_name_format: str,
                                                       raw_episode_file_name_format: str,
                                                       episode_file_name_format: str,
                                                       titleless_episode_file_name_format: str,
                                                       episode_number_padding: int = 2,
                                                       season_number_padding: int = 2,
                                                       season_directory_number_padding: int = 1,
                                                       ) -> TrackedAnimeProcessingSettings:
        settings = TrackedAnimeProcessingSettings(
            tracked_anime_id=tracked_anime_id,
            episode_number_padding=episode_number_padding,
            season_number_padding=season_number_padding,
            raw_episode_file_name_format=raw_episode_file_name_format,
            season_directory_number_padding=season_directory_number_padding,
            season_directory_name_format=season_directory_name_format,
            episode_file_name_format=episode_file_name_format,
            titleless_episode_file_name_format=titleless_episode_file_name_format,
        )
        self._session.add(settings)
        await self._session.flush()
        return settings

    async def get_tracked_anime_processing_settings(self,
                                                    tracked_anime_id: int,
                                                    load_relations: bool = False
                                                    ) -> TrackedAnimeProcessingSettings | None:
        query = select(TrackedAnimeProcessingSettings).where(
            TrackedAnimeProcessingSettings.tracked_anime_id == tracked_anime_id
        )
        if load_relations:
            query = query.options(joinedload(TrackedAnimeProcessingSettings.tracked_anime))
        return (await self._session.execute(query)).unique().scalar_one_or_none()

    async def get_tracked_anime_processing_settings_list(self,
                                                         tracked_anime_ids: Iterable[int],
                                                         load_relations: bool = False
                                                         ) -> list[TrackedAnimeProcessingSettings]:
        if not tracked_anime_ids:
            return []
        query = select(TrackedAnimeProcessingSettings).where(
            TrackedAnimeProcessingSettings.tracked_anime_id.in_(tracked_anime_ids)
        )
        if load_relations:
            query = query.options(joinedload(TrackedAnimeProcessingSettings.tracked_anime))
        return (await self._session.execute(query)).unique().scalars().all()

    async def get_all_active_tracked_anime_processing_settings(self):
        query = select(TrackedAnimeProcessingSettings) \
            .join(TrackedAnime) \
            .where(TrackedAnime.status == TrackedAnimeStatus.ACTIVE)
        return (await self._session.execute(query)).unique().scalars().all()

    async def update_tracked_anime_processing_settings(self, settings_id: int, **update_data):
        if not update_data:
            return
        await self._session.execute(
            update(TrackedAnimeProcessingSettings).where(
                TrackedAnimeProcessingSettings.id == settings_id
            ).values(**update_data)
        )
        await self._session.flush()

    async def delete_tracked_anime_processing_settings(self, settings_id: int):
        await self._session.execute(
            delete(TrackedAnimeProcessingSettings).where(
                TrackedAnimeProcessingSettings.id == settings_id
            )
        )
