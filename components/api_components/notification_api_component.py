from common.decorators import api_component
from common.exceptions import NotFoundException
from components import BaseComponent
from constants import NotificationStatus
from api.schemas.notification_schemas import NotificationListRequest, NotificationListResponse, NotificationListItem


class NotificationAPIComponent(BaseComponent):

    def __init__(self):
        from components.notification_component import NotificationComponent
        super().__init__()
        self._notification_component = NotificationComponent()

    @api_component
    async def get_notifications(self, params: NotificationListRequest) -> NotificationListResponse:
        notifications = await self._notification_component \
            .get_notifications(statuses=params.statuses, sort_direction=params.sort_direction,
                               limit=params.limit, offset=params.offset)
        return NotificationListResponse(notifications=[
            NotificationListItem(
                id=notification.id,
                code=notification.code,
                level=notification.level,
                text=notification.text,
                identifier=notification.identifier,
                status=notification.status,
                effective_at=notification.effective_at,
            ) for notification in notifications
        ])

    @api_component
    async def mark_notification_as_read(self, notification_id: int):
        if not (await self._notification_component.get_notification(notification_id=notification_id)):
            raise NotFoundException(f"Notification with ID {notification_id} not found")
        await self._notification_component.update_notification(
            notification_id=notification_id, status=NotificationStatus.READ
        )

    @api_component
    async def mark_notification_as_unread(self, notification_id: int):
        if not (await self._notification_component.get_notification(notification_id=notification_id)):
            raise NotFoundException(f"Notification with ID {notification_id} not found")
        await self._notification_component.update_notification(
            notification_id=notification_id, status=NotificationStatus.UNREAD
        )

    @api_component
    async def mark_notifications_as_read(self):
        await self._notification_component.mark_unread_notifications_as_read()
