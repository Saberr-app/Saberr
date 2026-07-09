from datetime import datetime

from pydantic import BaseModel

from constants import AppContext


class Status(BaseModel):

    class ServiceStatus(BaseModel):
        name: str
        healthy: bool
        error_level: str | None = None
        error_details: str | None = None
        error_code: int | None = None

    version: str
    ui_minimum_version: str
    context: AppContext
    unread_notification_count: int
    unread_error_notification_count: int
    settings_last_updated_at: datetime
    tracked_anime_last_updated_at: datetime
    anime_list_last_refreshed_at: datetime
    download_last_added_at: datetime
    services_status: dict[str, ServiceStatus]
    remote_update_available: bool


class StatusStream(BaseModel):
    ref: int
    ver: str | None = None
    ui_min_ver: str | None = None
    notif: int | None = None
    err_notif: int | None = None
    settings_updated: datetime | None = None
    tracked_updated: datetime | None = None
    list_refreshed: datetime | None = None
    download_added: datetime | None = None
    services_updated: datetime | None = None
    remote_update_available: bool | None = None
