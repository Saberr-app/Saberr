from app_state import downstream_healthcheck_workers, global_status
from common.decorators import api_component, require_db_session
from components import BaseComponent
from components.notification_component import NotificationComponent
from config import config
from constants import NotificationStatus, NotificationLevel
from api.schemas.status_schemas import Status, StatusStream


class StatusAPIComponent(BaseComponent):

    @api_component
    async def get_status(self) -> Status:

        if global_status.notification_count_stale:
            unread_notifications = await NotificationComponent().get_notifications(statuses=[NotificationStatus.UNREAD],
                                                                                   limit=100)
            unread_notification_count, unread_error_notification_count = 0, 0
            for unread_notification in unread_notifications:
                if unread_notification.level == NotificationLevel.ERROR:
                    unread_error_notification_count += 1
                unread_notification_count += 1
            global_status.unread_notification_count = unread_notification_count
            global_status.unread_error_notification_count = unread_error_notification_count
            global_status.notification_count_stale = False
        else:
            unread_notification_count = global_status.unread_notification_count
            unread_error_notification_count = global_status.unread_error_notification_count

        service_statuses = downstream_healthcheck_workers.get_statuses_data(compact=True)

        return Status(
            version=config.app_version.original_version_string,
            ui_minimum_version=config.ui_minimum_version.original_version_string,
            context=config.context,
            unread_notification_count=unread_notification_count,
            unread_error_notification_count=unread_error_notification_count,
            settings_last_updated_at=global_status.settings_last_updated,
            tracked_anime_last_updated_at=global_status.tracked_anime_last_updated,
            anime_list_last_refreshed_at=global_status.anime_list_last_refreshed,
            download_last_added_at=global_status.download_last_added,
            services_status=service_statuses,
            remote_update_available=global_status.remote_update_available
        )

    @require_db_session
    @api_component
    async def get_status_stream_data(self, ref: int):
        status = await self.get_status()
        return StatusStream(
            ref=ref,
            ver=config.app_version.original_version_string,
            ui_min_ver=config.ui_minimum_version.original_version_string,
            notif=status.unread_notification_count,
            err_notif=status.unread_error_notification_count,
            settings_updated=global_status.settings_last_updated,
            tracked_updated=global_status.tracked_anime_last_updated,
            list_refreshed=global_status.anime_list_last_refreshed,
            download_added=global_status.download_last_added,
            services_updated=global_status.services_status_last_changed,
            remote_update_available=global_status.remote_update_available,
        )
