from dataclasses import dataclass

import pytest

from constants import (AuditLogCode, ExternalServiceCode, ExternalServiceErrorLevel as Level,
                       NotificationLevel)
from tests.support.builders import make_service_status


@dataclass
class Case:
    id: str
    old: dict
    new: dict
    send_notification_on_change: bool
    expected_notifications: int
    expected_audit_logs: int
    expected_audit_code: AuditLogCode | None = None
    expected_notification_level: NotificationLevel | None = None


def _status(**kwargs):
    return make_service_status(**kwargs)


def _by_code(status):
    return {status.code: status}


_QBIT = dict(name="qBittorrent", code=ExternalServiceCode.QBIT)


CASES = [
    Case(id="no change does nothing",
         old=_by_code(_status(**_QBIT)),
         new=_by_code(_status(**_QBIT)),
         send_notification_on_change=True,
         expected_notifications=0, expected_audit_logs=0),
    Case(id="healthy -> down notifies and logs offline",
         old=_by_code(_status(**_QBIT)),
         new=_by_code(_status(**_QBIT, healthy=False, error_level=Level.DOWN,
                              error_details="boom", error_code=500)),
         send_notification_on_change=True,
         expected_notifications=1, expected_audit_logs=1,
         expected_audit_code=AuditLogCode.SERVICE_SET_OFFLINE,
         expected_notification_level=NotificationLevel.ERROR),
    Case(id="down -> healthy logs online without notification",
         old=_by_code(_status(**_QBIT, healthy=False, error_level=Level.DOWN)),
         new=_by_code(_status(**_QBIT)),
         send_notification_on_change=True,
         expected_notifications=0, expected_audit_logs=1,
         expected_audit_code=AuditLogCode.SERVICE_SET_ONLINE),
    Case(id="change into NOT_CONFIGURED is ignored",
         old=_by_code(_status(name="Anilist", code=ExternalServiceCode.ANILIST)),
         new=_by_code(_status(name="Anilist", code=ExternalServiceCode.ANILIST, healthy=False,
                              error_level=Level.NOT_CONFIGURED,
                              error_details="No user token set for Anilist client.", error_code=401)),
         send_notification_on_change=True,
         expected_notifications=0, expected_audit_logs=0),
    Case(id="error-level change between unhealthy states notifies again",
         old=_by_code(_status(**_QBIT, healthy=False, error_level=Level.DOWN)),
         new=_by_code(_status(**_QBIT, healthy=False, error_level=Level.AUTH_ISSUE,
                              error_details="nope", error_code=401)),
         send_notification_on_change=True,
         expected_notifications=1, expected_audit_logs=1,
         expected_audit_code=AuditLogCode.SERVICE_SET_OFFLINE),
    Case(id="suppressed when send_notification_on_change is False (still audits)",
         old=_by_code(_status(**_QBIT)),
         new=_by_code(_status(**_QBIT, healthy=False, error_level=Level.DOWN,
                              error_details="boom", error_code=500)),
         send_notification_on_change=False,
         expected_notifications=0, expected_audit_logs=1,
         expected_audit_code=AuditLogCode.SERVICE_SET_OFFLINE),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_handle_status_change_notifications(case: Case, make_worker, patched_components):
    notification, audit = patched_components
    worker = make_worker()

    await worker._handle_status_change_notifications(
        case.old, case.new, send_notification_on_change=case.send_notification_on_change)

    assert notification.send_notification.await_count == case.expected_notifications
    assert audit.log_service_changed_status.await_count == case.expected_audit_logs

    if case.expected_audit_code is not None:
        assert audit.log_service_changed_status.await_args.kwargs["code"] is case.expected_audit_code
    if case.expected_notification_level is not None:
        assert notification.send_notification.await_args.kwargs["level"] is case.expected_notification_level
