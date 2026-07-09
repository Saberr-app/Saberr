import re
from datetime import datetime, UTC
from typing import Iterable

from sqlalchemy import select, delete
from sqlalchemy.dialects.mysql import insert

from dto.orm_models import AnilistAnime, TrackedAnime, AnilistListItem, AnilistAnimeExtras, MappingOverride
from repositories import BaseRepo


class AnilistAnimeRepo(BaseRepo):

    async def get_anilist_anime_list(self, anime_ids: Iterable[int]) -> list[AnilistAnime]:
        query = select(AnilistAnime).where(AnilistAnime.anilist_id.in_(anime_ids))
        return (await self._session.execute(query)).scalars().all()
    
    async def bulk_upsert_anilist_anime(self, data_list: list[dict]):
        if not data_list:
            return
        insert_statement = insert(AnilistAnime).values(data_list)
        statement = insert_statement.on_duplicate_key_update(
            data=insert_statement.inserted.data,
            updated_at=datetime.now(UTC)
        )
        await self._session.execute(statement)
        await self._session.flush()
    
    async def delete_anilist_anime(self, anime_id: int):
        await self._session.execute(
            delete(AnilistAnime).where(AnilistAnime.anilist_id == anime_id)
        )
    
    async def delete_orphans_updated_older_than(self, older_than: datetime):
        await self._session.execute(
            delete(AnilistAnime)
            .where(AnilistAnime.updated_at < older_than)
            .where(AnilistAnime.anilist_id.not_in(select(TrackedAnime.anilist_id)))
            .where(AnilistAnime.anilist_id.not_in(select(AnilistListItem.anilist_id)))
            .where(AnilistAnime.anilist_id.not_in(select(MappingOverride.anilist_id)))
        )
        await self._session.flush()

    async def get_updated_older_than(self, older_than: datetime) -> list[AnilistAnime]:
        return (await self._session.execute(
            select(AnilistAnime).where(AnilistAnime.updated_at < older_than)
        )).scalars().all()

    async def upsert_anilist_anime_extras(self, anilist_id: int, data: dict):
        if not data:
            return
        insert_stmt = insert(AnilistAnimeExtras).values(
            anilist_id=anilist_id,
            data=data,
            updated_at=datetime.now(UTC)
        )
        await self._session.execute(
            insert_stmt.on_duplicate_key_update(data=data)
        )
        await self._session.flush()

    async def get_anilist_anime_extras(self, anilist_id: int) -> AnilistAnime | None:
        query = select(AnilistAnimeExtras).where(AnilistAnimeExtras.anilist_id == anilist_id)
        return (await self._session.execute(query)).unique().scalar_one_or_none()

    async def delete_orphan_extras_updated_older_than(self, older_than: datetime):
        await self._session.execute(
            delete(AnilistAnimeExtras)
            .where(AnilistAnimeExtras.updated_at < older_than)
            .where(AnilistAnimeExtras.anilist_id.not_in(select(AnilistAnime.anilist_id)))
        )
        await self._session.flush()

    async def search_anime(self, search_query: str) -> list[AnilistAnime]:
        tokens = [f'+{token.strip()}*' for token in re.sub(r'[+\-*"()~<>@|]', ' ', search_query).split()
                  if token.strip()]
        if not tokens:
            return []
        match_expr = AnilistAnime.search_blob.match(' '.join(tokens), in_boolean_mode=True)
        query = (
            select(AnilistAnime)
            .where(match_expr)
            .order_by(match_expr.desc())
        )
        return (await self._session.execute(query)).scalars().all()
