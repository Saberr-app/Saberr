from dataclasses import dataclass

import pytest

from components.notification_component import NotificationComponent
from constants import NotificationStatus

_REPO = "repositories.notification_repo.NotificationRepo"


@dataclass
class Case:
    id: str


CASES = [
    Case(id="flips all UNREAD notifications to READ via the repo"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_mark_unread_notifications_as_read(case: Case, mocker):
    repo = mocker.patch(f"{_REPO}.update_notifications_by_status")

    await NotificationComponent().mark_unread_notifications_as_read()

    repo.assert_awaited_once_with(current_status=NotificationStatus.UNREAD, status=NotificationStatus.READ)
