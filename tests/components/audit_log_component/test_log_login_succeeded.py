from dataclasses import dataclass

import pytest

from components.audit_log_component import AuditLogComponent
from constants import AuditLogCategory, AuditLogCode


@dataclass
class Case:
    id: str
    ip_address: str
    browser: str
    country: str | None
    expected_category: AuditLogCategory
    expected_text: str
    expected_data: dict
    expected_context_id: str


CASES = [
    Case(id="creates login succeeded row",
         ip_address="1.2.3.4", browser="UA", country="US",
         expected_category=AuditLogCategory.APP,
         expected_text="User login succeeded",
         expected_data={"ip_address": "1.2.3.4", "browser": "UA", "country": "US"},
         expected_context_id="default-context-"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_log_login_succeeded(case: Case, mocker):
    repo_create = mocker.patch("repositories.audit_log_repo.AuditLogRepo.create_audit_log")

    await AuditLogComponent().log_login_succeeded(
        ip_address=case.ip_address, browser=case.browser, country=case.country)

    repo_create.assert_awaited_once_with(
        code=AuditLogCode.LOGIN_SUCCEEDED, category=case.expected_category,
        text=case.expected_text, data=case.expected_data, context_id=case.expected_context_id)
