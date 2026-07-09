from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta

import pytest

from components.notification_component import NotificationComponent
from constants import NotificationStatus


@dataclass
class Case:
    id: str
    kwargs: dict
    expected_update_data: dict = field(default_factory=dict)


_NEW_TIME = (datetime.now(UTC) + timedelta(days=1)).replace(microsecond=0)


CASES = [
    Case(id="updates status only",
         kwargs={"status": NotificationStatus.READ},
         expected_update_data={"status": NotificationStatus.READ}),
    Case(id="updates effective_at only",
         kwargs={"effective_at": _NEW_TIME},
         expected_update_data={"effective_at": _NEW_TIME}),
    Case(id="updates both",
         kwargs={"status": NotificationStatus.READ, "effective_at": _NEW_TIME},
         expected_update_data={"status": NotificationStatus.READ, "effective_at": _NEW_TIME}),
    Case(id="no-op fields are not forwarded",
         kwargs={}, expected_update_data={}),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_notification(case: Case, mocker):
    repo_update = mocker.patch(
        "repositories.notification_repo.NotificationRepo.update_notification")

    await NotificationComponent().update_notification(notification_id=42, **case.kwargs)

    repo_update.assert_awaited_once_with(notification_id=42, **case.expected_update_data)
