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
    Case(id="creates anilist list refreshed row",
         expected_category=AuditLogCategory.ANILIST,
         expected_text="Refreshed cached user's Anilist anime list"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_log_user_anime_list_refreshed(case: Case, mocker):
    repo_create = mocker.patch("repositories.audit_log_repo.AuditLogRepo.create_audit_log")

    await AuditLogComponent().log_user_anime_list_refreshed()

    repo_create.assert_awaited_once_with(
        code=AuditLogCode.ANILIST_LIST_REFRESHED, category=case.expected_category,
        text=case.expected_text, data=case.expected_data, context_id="default-context-")
