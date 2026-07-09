from dataclasses import dataclass

import pytest

from components.api_components.login_api_component import LoginAPIComponent

_AUDIT = "components.audit_log_component.AuditLogComponent"


@dataclass
class Case:
    id: str
    succeeded: bool


CASES = [
    Case(id="success logs a succeeded login", succeeded=True),
    Case(id="failure logs a failed login", succeeded=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test__audit_login(case: Case, mocker):
    succeeded = mocker.patch(f"{_AUDIT}.log_login_succeeded")
    failed = mocker.patch(f"{_AUDIT}.log_login_failed")

    await LoginAPIComponent()._audit_login(case.succeeded, ip_address="1.2.3.4", browser="Firefox",
                                           country="US", username="bob")

    if case.succeeded:
        succeeded.assert_awaited_once_with(ip_address="1.2.3.4", browser="Firefox", country="US")
        failed.assert_not_awaited()
    else:
        failed.assert_awaited_once_with(ip_address="1.2.3.4", browser="Firefox", country="US", username="bob")
        succeeded.assert_not_awaited()
