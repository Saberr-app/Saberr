from dataclasses import dataclass

import pytest

from common.exceptions import ExternalServiceException
from config import config
from constants import ExternalServiceErrorLevel as Level, NotificationCode


@pytest.fixture(autouse=True)
def _configured_qbit(monkeypatch):
    # qBit healthcheck only runs when a base url is configured; configure it so the worker is "all healthy".
    monkeypatch.setattr(config.user_settings, "qbit_base_url", "http://qbit.test")


@dataclass
class Case:
    id: str
    qbit_exception: Exception | None = None
    expected_all_healthy: bool = False
    expected_notifications: int = 0
    expected_audit_logs: int = 0
    expected_notification_code: NotificationCode | None = None
    expected_notification_identifier: dict | None = None
    expected_qbit_down: bool = False
    expected_all_services_checked: bool = False


CASES = [
    Case(id="all healthy changes nothing and sends no notifications",
         expected_all_healthy=True,
         expected_notifications=0, expected_audit_logs=0),
    Case(id="service going down notifies and logs for that service only",
         qbit_exception=ExternalServiceException(detail="boom", status_code=500),
         expected_qbit_down=True,
         expected_notifications=1, expected_audit_logs=1,
         expected_notification_code=NotificationCode.SERVICE_DOWN,
         expected_notification_identifier={'reason': 'boom', "service_code": "qbit"}),
    Case(id="runs every service check",
         expected_all_services_checked=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_check(case: Case, make_worker, patched_components):
    notification, audit = patched_components
    w = make_worker()
    if case.qbit_exception is not None:
        w._qbit_service.healthcheck.side_effect = case.qbit_exception

    await w.poll_downstream_status()

    if case.expected_all_healthy:
        assert all(status.healthy for status in w.get_statuses().values())

    if case.expected_qbit_down:
        assert w._qbit_status.healthy is False
        assert w._qbit_status.error_level is Level.DOWN

    assert notification.send_notification.await_count == case.expected_notifications
    assert audit.log_service_changed_status.await_count == case.expected_audit_logs

    if case.expected_notification_code is not None:
        assert notification.send_notification.await_args.kwargs["code"] is case.expected_notification_code
    if case.expected_notification_identifier is not None:
        assert notification.send_notification.await_args.kwargs["identifier"] == case.expected_notification_identifier

    if case.expected_all_services_checked:
        w._qbit_service.healthcheck.assert_awaited_once()
        w._anilist_service.healthcheck.assert_awaited_once()
        w._tvdb_service.healthcheck.assert_awaited_once()
        w._rss_service.healthcheck.assert_awaited_once()
        assert w._discord_webhook_service.healthcheck.await_count == 1
