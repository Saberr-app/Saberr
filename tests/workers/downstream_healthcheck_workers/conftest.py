from unittest.mock import AsyncMock, MagicMock

import pytest

from constants import ExternalServiceCode
from workers.downstream_healthcheck_workers import DownstreamHealthcheckWorkers, ServiceStatus


@pytest.fixture
def make_worker():
    """Build a worker without running its heavy __init__ (which constructs real services).

    Every external service is a mock with an async `healthcheck`; by default they all succeed and
    the optional-config attributes (anilist token, discord webhook urls) are present, so the
    out-of-the-box worker is fully healthy. Tests override only the service they exercise.
    """

    # noinspection PyProtectedMember
    def _make():
        w = DownstreamHealthcheckWorkers.__new__(DownstreamHealthcheckWorkers)

        w._qbit_status = ServiceStatus("qBittorrent", ExternalServiceCode.QBIT)
        w._anilist_status = ServiceStatus("Anilist", ExternalServiceCode.ANILIST)
        w._tvdb_status = ServiceStatus("TVDB", ExternalServiceCode.TVDB)
        w._rss_status = ServiceStatus("RSS", ExternalServiceCode.RSS)
        w._notifications_discord_webhook_status = ServiceStatus("Notifications Discord Webhook",
                                                                ExternalServiceCode.NOTIFICATIONS_DISCORD_WEBHOOK)

        w._qbit_service = MagicMock()
        w._qbit_service.healthcheck = AsyncMock()

        w._anilist_service = MagicMock()
        w._anilist_service.healthcheck = AsyncMock()
        w._anilist_service.user_token = "anilist-token"

        w._tvdb_service = MagicMock()
        w._tvdb_service.healthcheck = AsyncMock()

        w._rss_service = MagicMock()
        w._rss_service.healthcheck = AsyncMock()

        w._discord_webhook_service = MagicMock()
        w._discord_webhook_service.healthcheck = AsyncMock()
        w._discord_webhook_service.notifications_discord_webhook_url = "https://discord.test/notifs"

        return w

    return _make


@pytest.fixture
def patched_components(monkeypatch):
    """Replace the notification and audit-log components the worker imports lazily, so the status
    change handler runs against mocks rather than the real DB-backed components.

    Yields the (notification_component, audit_log_component) mock *instances* the worker will get.
    """
    notification = MagicMock()
    notification.send_notification = AsyncMock()
    # the handler dedupes by querying existing unread SERVICE_DOWN notifications first;
    # default to none so a newly-down service still notifies.
    notification.get_notifications = AsyncMock(return_value=[])
    audit = MagicMock()
    audit.log_service_changed_status = AsyncMock()

    monkeypatch.setattr("components.notification_component.NotificationComponent",
                        MagicMock(return_value=notification))
    monkeypatch.setattr("components.audit_log_component.AuditLogComponent",
                        MagicMock(return_value=audit))

    return notification, audit
