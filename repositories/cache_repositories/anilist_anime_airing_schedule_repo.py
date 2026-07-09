from datetime import datetime, UTC
from typing import Iterable

from sqlalchemy import select, delete
from sqlalchemy.dialects.mysql import insert

from dto.orm_models import AnilistAnimeAiringSchedule, AnilistAnime, AnilistAnimeMonthlyAiringSchedule
from repositories import BaseRepo


class AnilistAnimeAiringScheduleRepo(BaseRepo):

    async def get_anilist_anime_airing_schedule(
            self, anilist_id: int, minimum_airing_at: int | None = None
    ) -> list[AnilistAnimeAiringSchedule]:
        query = select(AnilistAnimeAiringSchedule).where(AnilistAnimeAiringSchedule.anilist_id == anilist_id)
        if minimum_airing_at:
            query = query.where(AnilistAnimeAiringSchedule.airing_at >= minimum_airing_at)
        return (await self._session.execute(query)).scalars().all()

    async def get_anilist_anime_airing_schedule_list(
            self, anime_ids: Iterable[int], minimum_airing_at: int | None = None
    ) -> list[AnilistAnimeAiringSchedule]:
        query = select(AnilistAnimeAiringSchedule).where(AnilistAnimeAiringSchedule.anilist_id.in_(anime_ids))
        if minimum_airing_at:
            query = query.where(AnilistAnimeAiringSchedule.airing_at >= minimum_airing_at)
        return (await self._session.execute(query)).scalars().all()

    async def bulk_upsert_anilist_anime_airing_schedule(self, data_list: list[dict]):
        if not data_list:
            return
        insert_statement = insert(AnilistAnimeAiringSchedule).values(data_list)
        statement = insert_statement.on_duplicate_key_update(
            airing_at=insert_statement.inserted.airing_at,
            updated_at=datetime.now(UTC)
        )
        await self._session.execute(statement)
        await self._session.flush()

    async def delete_by_ids(self, ids: list[int]):
        await self._session.execute(
            delete(AnilistAnimeAiringSchedule)
            .where(AnilistAnimeAiringSchedule.id.in_(ids))
        )
        await self._session.flush()

    async def delete_updated_older_than(self, older_than: datetime):
        await self._session.execute(
            delete(AnilistAnimeAiringSchedule)
            .where(AnilistAnimeAiringSchedule.updated_at < older_than)
            .where(AnilistAnimeAiringSchedule.anilist_id.not_in(select(AnilistAnime.anilist_id)))
        )
        await self._session.flush()

    async def delete_airing_at_older_than(self, airing_at: int):
        await self._session.execute(
            delete(AnilistAnimeAiringSchedule)
            .where(AnilistAnimeAiringSchedule.airing_at < airing_at)
            .where(AnilistAnimeAiringSchedule.anilist_id.not_in(select(AnilistAnime.anilist_id)))
        )
        await self._session.flush()

    async def bulk_upsert_anilist_anime_monthly_airing_schedule(self, data_list: list[dict]):
        if not data_list:
            return
        insert_statement = insert(AnilistAnimeMonthlyAiringSchedule).values(data_list)
        statement = insert_statement.on_duplicate_key_update(
            data=insert_statement.inserted.data,
            updated_at=datetime.now(UTC)
        )
        await self._session.execute(statement)
        await self._session.flush()

    async def get_monthly_airing_schedules(self,
                                           anilist_ids: Iterable[int],
                                           months: Iterable[datetime]) -> list[AnilistAnimeMonthlyAiringSchedule]:
        query = select(AnilistAnimeMonthlyAiringSchedule) \
            .where(AnilistAnimeMonthlyAiringSchedule.anilist_id.in_(anilist_ids)) \
            .where(AnilistAnimeMonthlyAiringSchedule.month.in_(months))
        return (await self._session.execute(query)).scalars().all()

    async def delete_monthly_updated_older_than(self, older_than: datetime):
        await self._session.execute(
            delete(AnilistAnimeMonthlyAiringSchedule)
            .where(AnilistAnimeMonthlyAiringSchedule.updated_at < older_than)
            .where(AnilistAnimeMonthlyAiringSchedule.anilist_id.not_in(select(AnilistAnime.anilist_id)))
        )
        await self._session.flush()
