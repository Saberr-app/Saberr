from typing import Annotated

from fastapi import Query

from api.routes import api_v1_router
from components.api_components.notification_api_component import NotificationAPIComponent
from api.schemas import DataEnvelope
from api.schemas.notification_schemas import NotificationListRequest, NotificationListResponse


@api_v1_router.get("/notifications", response_model=DataEnvelope[NotificationListResponse])
async def list_notifications(params: Annotated[NotificationListRequest, Query()]):
    return DataEnvelope(data=await NotificationAPIComponent().get_notifications(params=params))


@api_v1_router.put("/notifications/{notification_id}/read", status_code=204)
async def mark_notification_as_read(notification_id: int):
    await NotificationAPIComponent().mark_notification_as_read(notification_id=notification_id)


@api_v1_router.put("/notifications/{notification_id}/unread", status_code=204)
async def mark_notification_as_unread(notification_id: int):
    await NotificationAPIComponent().mark_notification_as_unread(notification_id=notification_id)


@api_v1_router.put("/notifications/read", status_code=204)
async def mark_all_notification_as_read():
    await NotificationAPIComponent().mark_notifications_as_read()
