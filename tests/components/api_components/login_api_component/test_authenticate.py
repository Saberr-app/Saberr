from dataclasses import dataclass

import pytest

from common.context_helpers import RequestMetadata
from common.exceptions import UnauthorizedException
from components.api_components.login_api_component import LoginAPIComponent
from constants import NotificationCode
from api.schemas.login_schemas import LoginRequest

_AUDIT = "components.audit_log_component.AuditLogComponent"
_NOTIF = "components.notification_component.NotificationComponent"
_LOGIN = "components.api_components.login_api_component"

# the root conftest seeds admin credentials as test/test
_GOOD = dict(username="test", password="test")


@dataclass
class Case:
    id: str
    username: str
    password: str
    succeeds: bool


CASES = [
    Case(id="valid credentials issue a token", username="test", password="test", succeeds=True),
    Case(id="wrong password is rejected", username="test", password="nope", succeeds=False),
    Case(id="wrong username is rejected", username="nobody", password="test", succeeds=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_authenticate(case: Case, mocker):
    succeeded = mocker.patch(f"{_AUDIT}.log_login_succeeded")
    failed = mocker.patch(f"{_AUDIT}.log_login_failed")
    notify = mocker.patch(f"{_NOTIF}.send_notification")
    mocker.patch(f"{_LOGIN}.get_request_metadata",
                 return_value=RequestMetadata(ip_address="1.2.3.4", country="US", browser="Firefox"))

    component = LoginAPIComponent()
    body = LoginRequest(username=case.username, password=case.password)
    call = component.authenticate(body=body)

    if not case.succeeds:
        with pytest.raises(UnauthorizedException):
            await call
        failed.assert_awaited_once()
        succeeded.assert_not_awaited()
        notify.assert_not_awaited()
        return

    result = await call
    assert isinstance(result.token, str) and result.token
    assert isinstance(result.expires_at, int)
    succeeded.assert_awaited_once()
    failed.assert_not_awaited()
    assert notify.await_args.kwargs["code"] == NotificationCode.LOGIN
