from dataclasses import dataclass
from typing import Any

import pytest

from components.audit_log_component import AuditLogComponent
from constants import AnilistTitleLanguage, AuditLogCategory, AuditLogCode


@dataclass
class Case:
    id: str
    setting_name: str
    old_value: Any
    new_value: Any
    expected_text: str
    expected_data: dict


CASES = [
    Case(id="bool values render as enabled/disabled",
         setting_name="Auto Download", old_value=False, new_value=True,
         expected_text="User changed setting 'Auto Download' from 'disabled' to 'enabled'",
         expected_data={"setting_name": "Auto Download", "old_value": False, "new_value": True}),
    Case(id="enum values stored and rendered as their value",
         setting_name="AniList Preferred Title Language",
         old_value=AnilistTitleLanguage.ROMAJI, new_value=AnilistTitleLanguage.ENGLISH,
         expected_text="User changed setting 'AniList Preferred Title Language' from 'Romaji' to 'English'",
         expected_data={"setting_name": "AniList Preferred Title Language",
                        "old_value": "Romaji", "new_value": "English"}),
    Case(id="none renders as empty",
         setting_name="Published URL", old_value=None, new_value="https://x",
         expected_text="User changed setting 'Published URL' from 'empty' to 'https://x'",
         expected_data={"setting_name": "Published URL", "old_value": None, "new_value": "https://x"}),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_log_setting_changed(case: Case, mocker):
    repo_create = mocker.patch("repositories.audit_log_repo.AuditLogRepo.create_audit_log")

    await AuditLogComponent().log_setting_changed(
        setting_name=case.setting_name, old_value=case.old_value, new_value=case.new_value)

    repo_create.assert_awaited_once_with(
        code=AuditLogCode.SETTING_CHANGED, category=AuditLogCategory.APP,
        text=case.expected_text, data=case.expected_data, context_id="default-context-")
