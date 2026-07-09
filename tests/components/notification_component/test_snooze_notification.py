from dataclasses import dataclass
from datetime import datetime, UTC, timedelta

import pytest

from components.notification_component import NotificationComponent


@dataclass
class Case:
    id: str
    snooze_duration: timedelta
    expected_min_future: timedelta


CASES = [
    Case(id="snooze pushes effective_at into the future",
         snooze_duration=timedelta(hours=2), expected_min_future=timedelta(hours=1)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_snooze_notification(case: Case, mocker):
    repo_update = mocker.patch(
        "repositories.notification_repo.NotificationRepo.update_notification")

    await NotificationComponent().snooze_notification(
        notification_id=7, snooze_duration=case.snooze_duration)

    repo_update.assert_awaited_once()
    passed = repo_update.await_args.kwargs
    assert passed["notification_id"] == 7
    assert passed["effective_at"] > datetime.now(UTC) + case.expected_min_future
