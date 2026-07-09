from dataclasses import dataclass, field

import pytest

from components.audit_log_component import AuditLogComponent
from constants import AuditLogCategory, AuditLogCode


@dataclass
class Case:
    id: str
    expected_category: AuditLogCategory
    expected_text: str
    expected_data: dict = field(default_factory=dict)


CASES = [
    Case(id="creates app exited row",
         expected_category=AuditLogCategory.APP,
         expected_text="Saberr is exiting"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_log_app_exiting(case: Case, mocker):
    repo_create = mocker.patch("repositories.audit_log_repo.AuditLogRepo.create_audit_log")

    await AuditLogComponent().log_app_exiting()

    repo_create.assert_awaited_once_with(
        code=AuditLogCode.APP_EXITED, category=case.expected_category,
        text=case.expected_text, data=case.expected_data, context_id="default-context-")
