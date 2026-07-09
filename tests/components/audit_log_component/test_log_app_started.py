from dataclasses import dataclass

import pytest

from components.audit_log_component import AuditLogComponent
from constants import AuditLogCategory, AuditLogCode


@dataclass
class Case:
    id: str
    app_version: str
    expected_category: AuditLogCategory
    expected_text: str
    expected_data: dict


CASES = [
    Case(id="creates app started row",
         app_version="1.2.3",
         expected_category=AuditLogCategory.APP,
         expected_text="Saberr is starting",
         expected_data={"app_version": "1.2.3"}),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_log_app_started(case: Case, mocker):
    repo_create = mocker.patch("repositories.audit_log_repo.AuditLogRepo.create_audit_log")

    await AuditLogComponent().log_app_started(app_version=case.app_version)

    repo_create.assert_awaited_once_with(
        code=AuditLogCode.APP_STARTED, category=case.expected_category,
        text=case.expected_text, data=case.expected_data, context_id="default-context-")
