from dataclasses import dataclass

import pytest

from components.notification_component import NotificationComponent
from constants import NotificationCode, NotificationLevel


@dataclass
class Case:
    id: str
    found: bool
    notification_id: int = 123


CASES = [
    Case(id="returns notification from repo", found=True),
    Case(id="returns none when repo has none", found=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_notification(case: Case, make_notification, mocker):
    expected = make_notification(
        code=NotificationCode.LOGIN, level=NotificationLevel.INFO, notification_id=case.notification_id
    ) if case.found else None
    repo_get = mocker.patch(
        "repositories.notification_repo.NotificationRepo.get_notification_by_id",
        return_value=expected)

    result = await NotificationComponent().get_notification(notification_id=case.notification_id)

    assert result is expected
    repo_get.assert_awaited_once_with(notification_id=case.notification_id)
