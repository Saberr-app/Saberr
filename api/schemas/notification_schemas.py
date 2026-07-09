from datetime import datetime

from pydantic import BaseModel

from constants import NotificationStatus, NotificationCode, NotificationLevel, SortDirection


class NotificationListRequest(BaseModel):
    statuses: list[NotificationStatus] = []
    sort_direction: SortDirection = SortDirection.DESC
    offset: int = 0
    limit: int = 20


class NotificationListItem(BaseModel):
    id: int
    code: NotificationCode
    level: NotificationLevel
    text: str
    identifier: dict | list | None
    status: NotificationStatus
    effective_at: datetime


class NotificationListResponse(BaseModel):
    notifications: list[NotificationListItem]
