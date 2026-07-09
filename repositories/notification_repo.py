from datetime import datetime, UTC

from sqlalchemy import select, update

from dto.orm_models import Notification
from constants import NotificationCode, NotificationStatus, NotificationLevel, SortDirection
from system import UNSET
from repositories import BaseRepo


class NotificationRepo(BaseRepo):

    # noinspection PyTypeChecker
    async def create_notification(self,
                                  code: NotificationCode,
                                  level: NotificationLevel,
                                  text: str,
                                  identifier: dict | list | None = None,
                                  status: NotificationStatus = NotificationStatus.UNREAD,
                                  effective_at: datetime = None) -> Notification:
        if effective_at is None:
            effective_at = datetime.now(UTC)
        notification = Notification(
            code=code,
            level=level,
            text=text,
            identifier=identifier,
            status=status,
            effective_at=effective_at
        )
        self._session.add(notification)
        await self._session.flush()
        return notification

    async def get_notification(self, code: NotificationCode, identifier: dict | list) -> Notification | None:
        query = (select(Notification)
                 .where(Notification.code == code, Notification.identifier == identifier)
                 .limit(1))
        return (await self._session.execute(query)).scalar_one_or_none()

    async def get_notification_by_id(self, notification_id: int) -> Notification | None:
        query = (select(Notification)
                 .where(Notification.id == notification_id))
        return (await self._session.execute(query)).scalar_one_or_none()

    async def get_notifications(self,
                                statuses: list[NotificationStatus] | None = None,
                                code: NotificationCode | None = None,
                                level: NotificationLevel | None = None,
                                identifier: dict | list | None = None,
                                after: datetime | None = None,
                                before: datetime | None = None,
                                effective_before: datetime | None = UNSET,
                                sort_direction: SortDirection = SortDirection.DESC,
                                limit: int | None = None,
                                offset: int | None = None) -> list[Notification]:
        if effective_before is UNSET:
            effective_before = datetime.now(UTC)
        query = select(Notification)
        if statuses:
            query = query.where(Notification.status.in_(statuses))
        if code:
            query = query.where(Notification.code == code)
        if level:
            query = query.where(Notification.level == level)
        if identifier:
            query = query.where(Notification.identifier == identifier)
        if after:
            query = query.where(Notification.created_at > after)
        if before:
            query = query.where(Notification.created_at < before)
        if effective_before:
            query = query.where(Notification.effective_at < effective_before)
        query = query.order_by(Notification.effective_at.asc() if sort_direction == SortDirection.ASC
                               else Notification.effective_at.desc())
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        return (await self._session.execute(query)).scalars().all()

    async def update_notification(self, notification_id: int, **update_data) -> None:
        await self._session.execute(
            update(Notification).where(Notification.id == notification_id).values(**update_data)
        )
        await self._session.flush()

    async def update_notifications_by_status(self, current_status: NotificationStatus, **update_data) -> None:
        await self._session.execute(
            update(Notification).where(Notification.status == current_status).values(**update_data)
        )
        await self._session.flush()
