from dataclasses import dataclass

import pytest

from common.exceptions import ExternalServiceException
from constants import ExternalServiceErrorLevel as Level, ExternalServiceCode
from workers.downstream_healthcheck_workers import ServiceStatus

_NAME = "Notifications Discord Webhook"
_CODE = ExternalServiceCode.NOTIFICATIONS_DISCORD_WEBHOOK


@dataclass
class Case:
    id: str
    webhook_url: str | None = "https://discord.test/notifs"
    healthcheck_exception: Exception | None = None
    pre_unhealthy: bool = False
    expected_status: ServiceStatus = None
    expected_webhook_url: str | None = None
    expected_healthcheck_awaited: bool = True


CASES = [
    Case(id="success with url resets status",
         pre_unhealthy=True,
         expected_status=ServiceStatus(_NAME, _CODE, checked=True),
         expected_webhook_url="https://discord.test/notifs"),
    Case(id="no url stays not configured even when healthcheck succeeds",
         webhook_url=None,
         expected_status=ServiceStatus(_NAME, _CODE, healthy=False, error_level=Level.NOT_CONFIGURED,
                                       error_details="No configured Discord webhook.", error_code=401,
                                       checked=True)),
    # no url short-circuits to NOT_CONFIGURED; the healthcheck is never attempted.
    Case(id="no url short circuits even when healthcheck would fail",
         webhook_url=None,
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=500),
         expected_status=ServiceStatus(_NAME, _CODE, healthy=False, error_level=Level.NOT_CONFIGURED,
                                       error_details="No configured Discord webhook.", error_code=401,
                                       checked=True),
         expected_healthcheck_awaited=False),
    Case(id="401-auth",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=401),
         expected_status=ServiceStatus(_NAME, _CODE, healthy=False, error_level=Level.AUTH_ISSUE,
                                       error_details="boom", error_code=401, checked=True)),
    Case(id="403-auth",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=403),
         expected_status=ServiceStatus(_NAME, _CODE, healthy=False, error_level=Level.AUTH_ISSUE,
                                       error_details="boom", error_code=403, checked=True)),
    Case(id="400-internal",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=400),
         expected_status=ServiceStatus(_NAME, _CODE, healthy=False, error_level=Level.INTERNAL_ERROR,
                                       error_details="boom", error_code=400, checked=True)),
    Case(id="500-down",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=500),
         expected_status=ServiceStatus(_NAME, _CODE, healthy=False, error_level=Level.DOWN,
                                       error_details="boom", error_code=500, checked=True)),
    Case(id="unknown-down",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=None),
         expected_status=ServiceStatus(_NAME, _CODE, healthy=False, error_level=Level.DOWN,
                                       error_details="boom", error_code=None, checked=True)),
    Case(id="unexpected exception is internal error",
         healthcheck_exception=ValueError("kaboom"),
         expected_status=ServiceStatus(_NAME, _CODE, healthy=False, error_level=Level.INTERNAL_ERROR,
                                       error_details="Unexpected error during healthcheck: kaboom",
                                       error_code=0, checked=True)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_check_notifications_discord_webhook(case: Case, make_worker):
    w = make_worker()
    w._discord_webhook_service.notifications_discord_webhook_url = case.webhook_url
    if case.pre_unhealthy:
        w._notifications_discord_webhook_status.healthy = False
        w._notifications_discord_webhook_status.error_level = Level.DOWN
    if case.healthcheck_exception is not None:
        w._discord_webhook_service.healthcheck.side_effect = case.healthcheck_exception

    await w._check_notifications_discord_webhook()

    assert w._notifications_discord_webhook_status == case.expected_status
    if case.expected_webhook_url is not None:
        w._discord_webhook_service.healthcheck.assert_awaited_once_with(webhook_url=case.expected_webhook_url)
    if not case.expected_healthcheck_awaited:
        w._discord_webhook_service.healthcheck.assert_not_awaited()
