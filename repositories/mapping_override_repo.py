
from sqlalchemy import select, update, delete, or_

from constants import MappingOverrideMode
from dto.orm_models import MappingOverride
from repositories import BaseRepo


class MappingOverrideRepo(BaseRepo):

    # noinspection PyTypeChecker
    async def create_mapping_override(self,
                                      anilist_id: int,
                                      anilist_episode_number_from: int,
                                      anilist_episode_number_to: int | None,
                                      tvdb_series_id: int,
                                      tvdb_season_number: int,
                                      tvdb_episode_number_from: int,
                                      tvdb_episode_number_to: int | None,
                                      granularity: int,
                                      mode: MappingOverrideMode) -> MappingOverride:
        mapping_override = MappingOverride(
            anilist_id=anilist_id,
            anilist_episode_number_from=anilist_episode_number_from,
            anilist_episode_number_to=anilist_episode_number_to,
            tvdb_series_id=tvdb_series_id,
            tvdb_season_number=tvdb_season_number,
            tvdb_episode_number_from=tvdb_episode_number_from,
            tvdb_episode_number_to=tvdb_episode_number_to,
            granularity=granularity,
            mode=mode,
        )
        self._session.add(mapping_override)
        await self._session.flush()
        return mapping_override

    async def get_all_mapping_overrides(self) -> list[MappingOverride]:
        query = select(MappingOverride).order_by(MappingOverride.updated_at.desc())
        return (await self._session.execute(query)).scalars().all()

    async def get_mapping_overrides_for_anime(self,
                                              anilist_id: int | None = None,
                                              tvdb_id: int | None = None) -> list[MappingOverride]:
        conditions = []
        if anilist_id is not None:
            conditions.append(MappingOverride.anilist_id == anilist_id)
        if tvdb_id is not None:
            conditions.append(MappingOverride.tvdb_series_id == tvdb_id)
        query = select(MappingOverride)
        if conditions:
            query = query.where(or_(*conditions))
        return (await self._session.execute(query)).scalars().all()

    async def get_mapping_override(self, override_id: int) -> MappingOverride | None:
        query = select(MappingOverride).where(MappingOverride.id == override_id)
        return (await self._session.execute(query)).scalar_one_or_none()

    async def update_mapping_override(self, override_id: int, data: dict) -> None:
        await self._session.execute(
            update(MappingOverride).where(MappingOverride.id == override_id).values(**data)
        )
        await self._session.flush()

    async def delete_mapping_override(self, override_id: int) -> None:
        await self._session.execute(
            delete(MappingOverride).where(MappingOverride.id == override_id)
        )
        await self._session.flush()
