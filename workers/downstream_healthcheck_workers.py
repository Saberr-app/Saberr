from copy import deepcopy
from dataclasses import dataclass

from common.decorators import periodic_worker, require_db_session
from common.exceptions import ExternalServiceException
from config import config
from constants import (ExternalServiceErrorLevel, NotificationCode, NotificationLevel, AuditLogCode,
                       ExternalServiceCode, NotificationStatus)
from workers import BaseWorkerClass


@dataclass
class ServiceStatus:
    name: str
    code: ExternalServiceCode
    healthy: bool = True
    error_level: ExternalServiceErrorLevel | None = None
    error_details: str | None = None
    error_code: int | None = None

    checked: bool = False

    def to_dict(self, compact: bool = False):
        status = {
            "name": self.name,
            "healthy": self.healthy,
        }
        if not compact or not self.healthy:
            status |= {
                "error_level": self.error_level.value if self.error_level else None,
                "error_details": self.error_details,
                "error_code": self.error_code,
            }
        return status

    def reset(self):
        self.healthy = True
        self.error_level = None
        self.error_details = None
        self.error_code = None


class DownstreamHealthcheckWorkers(BaseWorkerClass):
    NAME = "Downstream Healthcheck"

    def __init__(self):
        from services.anilist_service import AnilistService
        from services.discord_webhook_service import DiscordWebhookService
        from services.qbit_service import QBitService
        from services.rss_service import RSSService
        from services.tvdb_service import TVDBService
        super().__init__()

        self._qbit_status = ServiceStatus("qBittorrent", ExternalServiceCode.QBIT)
        self._anilist_status = ServiceStatus("Anilist", ExternalServiceCode.ANILIST)
        self._tvdb_status = ServiceStatus("TVDB", ExternalServiceCode.TVDB)
        self._rss_status = ServiceStatus("RSS", ExternalServiceCode.RSS)
        self._notifications_discord_webhook_status = ServiceStatus("Notifications Discord Webhook",
                                                                   ExternalServiceCode.NOTIFICATIONS_DISCORD_WEBHOOK)

        self._qbit_service = QBitService()
        self._anilist_service = AnilistService()
        self._tvdb_service = TVDBService()
        self._rss_service = RSSService()
        self._discord_webhook_service = DiscordWebhookService()

    @periodic_worker(frequency=180, initial_delay=5)
    async def poll_downstream_status(self, service_code: ExternalServiceCode = None,
                                     send_notification_on_change: bool = True):
        old_statuses = deepcopy(self.get_statuses())

        if service_code:
            match service_code:
                case ExternalServiceCode.QBIT:
                    await self._check_qbit()
                case ExternalServiceCode.ANILIST:
                    await self._check_anilist()
                case ExternalServiceCode.TVDB:
                    await self._check_tvdb()
                case ExternalServiceCode.RSS:
                    await self._check_rss()
                case ExternalServiceCode.NOTIFICATIONS_DISCORD_WEBHOOK:
                    await self._check_notifications_discord_webhook()
                case _:
                    raise ValueError(f"Invalid service code: {service_code}")
        else:
            await self._check_qbit()
            await self._check_anilist()
            await self._check_tvdb()
            await self._check_rss()
            await self._check_notifications_discord_webhook()

        await self._handle_status_change_notifications(old_statuses=old_statuses,
                                                       new_statuses=self.get_statuses(),
                                                       send_notification_on_change=send_notification_on_change)

    async def force_check(self, service_code: ExternalServiceCode = None):
        await self.poll_downstream_status(service_code=service_code, send_notification_on_change=False)

    async def _check_qbit(self):
        if not config.user_settings.qbit_base_url:
            self._qbit_status.healthy = False
            self._qbit_status.error_level = ExternalServiceErrorLevel.NOT_CONFIGURED
            self._qbit_status.error_details = "No host set for qBittorrent client."
            self._qbit_status.error_code = 401
        else:
            try:
                await self._qbit_service.healthcheck()
            except ExternalServiceException as e:
                if e.status_code in (401, 403):
                    error_level = ExternalServiceErrorLevel.AUTH_ISSUE
                elif e.status_code == 400:
                    error_level = ExternalServiceErrorLevel.INTERNAL_ERROR
                else:
                    error_level = ExternalServiceErrorLevel.DOWN
                self._qbit_status.healthy = False
                self._qbit_status.error_level = error_level
                self._qbit_status.error_details = e.detail
                self._qbit_status.error_code = e.status_code
            except Exception as e:
                self._qbit_status.healthy = False
                self._qbit_status.error_level = ExternalServiceErrorLevel.INTERNAL_ERROR
                self._qbit_status.error_details = f"Unexpected error during healthcheck: {e}"
                self._qbit_status.error_code = 0
            else:
                self._qbit_status.reset()
        self._qbit_status.checked = True

    async def _check_anilist(self):
        if not self._anilist_service.user_token:
            self._anilist_status.healthy = False
            self._anilist_status.error_level = ExternalServiceErrorLevel.NOT_CONFIGURED
            self._anilist_status.error_details = "No user token set for Anilist client."
            self._anilist_status.error_code = 401
        try:
            await self._anilist_service.healthcheck(with_auth=bool(self._anilist_service.user_token))
        except ExternalServiceException as e:
            if e.status_code in (401, 403):
                error_level = ExternalServiceErrorLevel.AUTH_ISSUE
            elif e.status_code == 400:
                error_level = ExternalServiceErrorLevel.INTERNAL_ERROR
            else:
                error_level = ExternalServiceErrorLevel.DOWN
            self._anilist_status.healthy = False
            self._anilist_status.error_level = error_level
            self._anilist_status.error_details = e.detail
            self._anilist_status.error_code = e.status_code
        except Exception as e:
            self._anilist_status.healthy = False
            self._anilist_status.error_level = ExternalServiceErrorLevel.INTERNAL_ERROR
            self._anilist_status.error_details = f"Unexpected error during healthcheck: {e}"
            self._anilist_status.error_code = 0
        else:
            if self._anilist_service.user_token:
                self._anilist_status.reset()
        finally:
            self._anilist_status.checked = True

    async def _check_tvdb(self):
        try:
            await self._tvdb_service.healthcheck()
        except ExternalServiceException as e:
            if e.status_code in (401, 403):
                error_level = ExternalServiceErrorLevel.AUTH_ISSUE
            elif e.status_code == 400:
                error_level = ExternalServiceErrorLevel.INTERNAL_ERROR
            else:
                error_level = ExternalServiceErrorLevel.DOWN
            self._tvdb_status.healthy = False
            self._tvdb_status.error_level = error_level
            self._tvdb_status.error_details = e.detail
            self._tvdb_status.error_code = e.status_code
        except Exception as e:
            self._tvdb_status.healthy = False
            self._tvdb_status.error_level = ExternalServiceErrorLevel.INTERNAL_ERROR
            self._tvdb_status.error_details = f"Unexpected error during healthcheck: {e}"
            self._tvdb_status.error_code = 0
        else:
            self._tvdb_status.reset()
        finally:
            self._tvdb_status.checked = True

    async def _check_rss(self):
        try:
            await self._rss_service.healthcheck()
        except ExternalServiceException as e:
            self._rss_status.healthy = False
            self._rss_status.error_level = ExternalServiceErrorLevel.DOWN \
                if e.status_code != 400 else ExternalServiceErrorLevel.INTERNAL_ERROR
            self._rss_status.error_details = e.detail
            self._rss_status.error_code = e.status_code
        except Exception as e:
            self._rss_status.healthy = False
            self._rss_status.error_level = ExternalServiceErrorLevel.INTERNAL_ERROR
            self._rss_status.error_details = f"Unexpected error during healthcheck: {e}"
            self._rss_status.error_code = 0
        else:
            self._rss_status.reset()
        finally:
            self._rss_status.checked = True

    async def _check_notifications_discord_webhook(self):
        if not self._discord_webhook_service.notifications_discord_webhook_url:
            self._notifications_discord_webhook_status.healthy = False
            self._notifications_discord_webhook_status.error_level = ExternalServiceErrorLevel.NOT_CONFIGURED
            self._notifications_discord_webhook_status.error_details = "No configured Discord webhook."
            self._notifications_discord_webhook_status.error_code = 401
        else:
            try:
                await self._discord_webhook_service.healthcheck(
                    webhook_url=self._discord_webhook_service.notifications_discord_webhook_url
                )
            except ExternalServiceException as e:
                if e.status_code in (401, 403):
                    error_level = ExternalServiceErrorLevel.AUTH_ISSUE
                elif e.status_code == 400:
                    error_level = ExternalServiceErrorLevel.INTERNAL_ERROR
                else:
                    error_level = ExternalServiceErrorLevel.DOWN
                self._notifications_discord_webhook_status.healthy = False
                self._notifications_discord_webhook_status.error_level = error_level
                self._notifications_discord_webhook_status.error_details = e.detail
                self._notifications_discord_webhook_status.error_code = e.status_code
            except Exception as e:
                self._notifications_discord_webhook_status.healthy = False
                self._notifications_discord_webhook_status.error_level = ExternalServiceErrorLevel.INTERNAL_ERROR
                self._notifications_discord_webhook_status.error_details = f"Unexpected error during healthcheck: {e}"
                self._notifications_discord_webhook_status.error_code = 0
            else:
                self._notifications_discord_webhook_status.reset()
        self._notifications_discord_webhook_status.checked = True

    @require_db_session
    async def _handle_status_change_notifications(self,
                                                  old_statuses: dict[ExternalServiceCode, ServiceStatus],
                                                  new_statuses: dict[ExternalServiceCode, ServiceStatus],
                                                  send_notification_on_change: bool):
        from components.audit_log_component import AuditLogComponent
        from components.notification_component import NotificationComponent
        notification_component = NotificationComponent()
        audit_log_component = AuditLogComponent()

        for service_code, new_status in new_statuses.items():
            old_status = old_statuses[service_code]
            if (new_status.healthy, new_status.error_level) != (old_status.healthy, old_status.error_level) \
                    and new_status.error_level != ExternalServiceErrorLevel.NOT_CONFIGURED:
                if not new_status.healthy and send_notification_on_change:
                    if not (await notification_component.get_notifications(
                            statuses=[NotificationStatus.UNREAD],
                            code=NotificationCode.SERVICE_DOWN,
                            identifier={"service_code": service_code.value,
                                        "reason": f"{new_status.error_details}"},
                            limit=None
                    )):
                        level = NotificationLevel.ERROR if new_status.code in [ExternalServiceCode.QBIT,
                                                                               ExternalServiceCode.RSS] \
                            else NotificationLevel.WARNING
                        await notification_component.send_notification(
                            code=NotificationCode.SERVICE_DOWN,
                            level=level,
                            text=f"**{new_status.name}** is down.",
                            identifier={"service_code": service_code.value,
                                        "reason": f"{new_status.error_details}"},
                            send_discord_notification=False
                        )
                await audit_log_component.log_service_changed_status(
                    code=AuditLogCode.SERVICE_SET_ONLINE if new_status.healthy else AuditLogCode.SERVICE_SET_OFFLINE,
                    current_status=new_status)
            if new_status != old_status:
                from app_state import global_status
                global_status.services_status_changed()

    def get_statuses_data(self, compact: bool = False) -> dict[str, dict]:
        statuses = {
            self._qbit_status.code.value:
                self._qbit_status.to_dict(compact=compact),
            self._anilist_status.code.value:
                self._anilist_status.to_dict(compact=compact),
            self._tvdb_status.code.value:
                self._tvdb_status.to_dict(compact=compact),
            self._rss_status.code.value:
                self._rss_status.to_dict(compact=compact),
            self._notifications_discord_webhook_status.code.value:
                self._notifications_discord_webhook_status.to_dict(compact=compact),
        }
        return statuses

    def get_statuses(self) -> dict[ExternalServiceCode, 'ServiceStatus']:
        return {
            self._qbit_status.code: self._qbit_status,
            self._anilist_status.code: self._anilist_status,
            self._tvdb_status.code: self._tvdb_status,
            self._rss_status.code: self._rss_status,
            self._notifications_discord_webhook_status.code: self._notifications_discord_webhook_status,
        }

    def get_status(self, service_code: ExternalServiceCode | str) -> ServiceStatus:
        if isinstance(service_code, str):
            service_code = ExternalServiceCode(service_code)
        match service_code:
            case ExternalServiceCode.QBIT:
                return self._qbit_status
            case ExternalServiceCode.ANILIST:
                return self._anilist_status
            case ExternalServiceCode.TVDB:
                return self._tvdb_status
            case ExternalServiceCode.RSS:
                return self._rss_status
            case ExternalServiceCode.NOTIFICATIONS_DISCORD_WEBHOOK:
                return self._notifications_discord_webhook_status
            case _:
                raise ValueError(f"Unknown service code: {service_code}")
