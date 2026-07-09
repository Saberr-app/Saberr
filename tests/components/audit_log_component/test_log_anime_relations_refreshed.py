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
    Case(id="creates anime relations refreshed row",
         expected_category=AuditLogCategory.OTHER,
         expected_text="Refreshed anime relations data"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_log_anime_relations_refreshed(case: Case, mocker):
    repo_create = mocker.patch("repositories.audit_log_repo.AuditLogRepo.create_audit_log")

    await AuditLogComponent().log_anime_relations_refreshed()

    repo_create.assert_awaited_once_with(
        code=AuditLogCode.ANIME_RELATIONS_REFRESHED, category=case.expected_category,
        text=case.expected_text, data=case.expected_data, context_id="default-context-")
