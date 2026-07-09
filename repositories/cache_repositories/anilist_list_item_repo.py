from typing import Iterable

from sqlalchemy import select, delete
from sqlalchemy.dialects.mysql import insert

from dto.orm_models import AnilistListItem
from repositories import BaseRepo


class AnilistListItemRepo(BaseRepo):

    # noinspection PyTypeChecker
    async def create_anilist_list_item(self,
                                       anilist_id: int,
                                       data: dict) -> AnilistListItem:
        anilist_list_item = AnilistListItem(
            anilist_id=anilist_id,
            data=data
        )
        self._session.add(anilist_list_item)
        await self._session.flush()
        return anilist_list_item

    async def bulk_upsert_anilist_list_item(self, data_list: list[dict]) -> bool:
        if not data_list:
            return False
        insert_statement = insert(AnilistListItem).values(data_list)
        statement = insert_statement.on_duplicate_key_update(
            data=insert_statement.inserted.data
        )
        result = await self._session.execute(statement)
        # noinspection PyUnresolvedReferences
        return result.rowcount > 0

    async def upsert_anilist_list_item(self, anilist_id: int, data: dict):
        if not data:
            return
        insert_stmt = insert(AnilistListItem).values(
            anilist_id=anilist_id,
            data=data
        )
        await self._session.execute(
            insert_stmt.on_duplicate_key_update(data=data)
        )
        await self._session.flush()

    async def get_anilist_list_item(self, anilist_id: int) -> AnilistListItem | None:
        query = select(AnilistListItem).where(AnilistListItem.anilist_id == anilist_id)
        return (await self._session.execute(query)).unique().scalar_one_or_none()

    async def get_anilist_list_items(self, anilist_ids: Iterable[int]) -> list[AnilistListItem]:
        query = select(AnilistListItem).where(AnilistListItem.anilist_id.in_(anilist_ids))
        return (await self._session.execute(query)).scalars().all()

    async def get_anilist_list(self) -> list[AnilistListItem]:
        query = select(AnilistListItem)
        return (await self._session.execute(query)).scalars().all()

    async def delete_all(self, exclude_anilist_ids: Iterable[int] | None = None) -> bool:
        query = delete(AnilistListItem)
        if exclude_anilist_ids:
            query = query.where(AnilistListItem.anilist_id.not_in(exclude_anilist_ids))
        else:
            query = query.where(AnilistListItem.id > 0)
        result = await self._session.execute(query)
        await self._session.flush()
        # noinspection PyUnresolvedReferences
        return result.rowcount > 0

    async def delete_list_item(self, anilist_id: int):
        await self._session.execute(delete(AnilistListItem).where(AnilistListItem.anilist_id == anilist_id))
        await self._session.flush()

    async def delete_list_items(self, anilist_ids: list[int]):
        await self._session.execute(delete(AnilistListItem).where(AnilistListItem.anilist_id.in_(anilist_ids)))
        await self._session.flush()
