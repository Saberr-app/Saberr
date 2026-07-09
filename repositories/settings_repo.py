from datetime import datetime

from sqlalchemy import select, update

from constants import SettingsCode
from dto.orm_models import Settings
from repositories import BaseRepo


class SettingsRepo(BaseRepo):

    async def get_all_settings(self) -> list[Settings]:
        query = select(Settings)
        return (await self._session.execute(query)).scalars().all()

    async def get_setting(self, code: SettingsCode) -> Settings | None:
        query = select(Settings).where(Settings.code == code)
        return (await self._session.execute(query)).unique().scalar_one_or_none()

    async def update_setting(self, code: SettingsCode, data: any) -> None:
        await self._session.execute(
            update(Settings).where(Settings.code == code).values(data=data)
        )
        await self._session.flush()

    async def get_latest_updated_at(self) -> datetime:
        query = select(Settings.updated_at).order_by(Settings.updated_at.desc()).limit(1)
        return (await self._session.execute(query)).unique().scalar_one_or_none()
