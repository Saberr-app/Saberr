from dataclasses import dataclass
from datetime import datetime, UTC

import pytest

from components.notification_component import NotificationComponent
from constants import NotificationCode, NotificationLevel, NotificationStatus, SortDirection
from system import UNSET


@dataclass
class Case:
    id: str
    kwargs: dict
    expect_effective_before_now: bool


CASES = [
    Case(id="defaults effective_before to now when omitted",
         kwargs={}, expect_effective_before_now=True),
    Case(id="passes effective_before=None through unchanged",
         kwargs={"effective_before": None}, expect_effective_before_now=False),
    Case(id="forwards filters to the repo",
         kwargs={"statuses": [NotificationStatus.UNREAD], "level": NotificationLevel.INFO,
                 "code": NotificationCode.LOGIN, "sort_direction": SortDirection.ASC,
                 "limit": 5, "offset": 2, "effective_before": None},
         expect_effective_before_now=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_notifications(case: Case, make_notification, mocker):
    expected = [make_notification(code=NotificationCode.LOGIN, level=NotificationLevel.INFO)]
    repo_get = mocker.patch(
        "repositories.notification_repo.NotificationRepo.get_notifications", return_value=expected)

    before = datetime.now(UTC)
    result = await NotificationComponent().get_notifications(**case.kwargs)
    after = datetime.now(UTC)

    assert result is expected
    passed = repo_get.await_args.kwargs
    if case.expect_effective_before_now:
        assert before <= passed["effective_before"] <= after
    else:
        assert passed["effective_before"] == case.kwargs.get("effective_before")
    # remaining filters forwarded verbatim
    for key, value in case.kwargs.items():
        if key == "effective_before" and value is UNSET:
            continue
        assert passed[key] == value
