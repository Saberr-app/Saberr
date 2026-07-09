from dataclasses import dataclass

import pytest

from common.exceptions import NotFoundException
from components.api_components.notification_api_component import NotificationAPIComponent
from constants import NotificationCode, NotificationLevel, NotificationStatus

LEVEL = list(NotificationLevel)[0]


@dataclass
class Case:
    id: str
    found: bool
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="marks found notification unread", found=True),
    Case(id="missing notification raises not found", found=False,
         expected_exception=NotFoundException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_mark_notification_as_unread(case: Case, make_notification, mocker):
    found = make_notification(code=NotificationCode.LOGIN, level=LEVEL,
                              status=NotificationStatus.READ) if case.found else None
    mocker.patch("components.notification_component.NotificationComponent.get_notification",
                 return_value=found)
    update = mocker.patch(
        "components.notification_component.NotificationComponent.update_notification")

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await NotificationAPIComponent().mark_notification_as_unread(notification_id=999999)
        update.assert_not_awaited()
        return

    await NotificationAPIComponent().mark_notification_as_unread(notification_id=found.id)
    update.assert_awaited_once_with(notification_id=found.id, status=NotificationStatus.UNREAD)
