from dataclasses import dataclass

import pytest

from components.api_components.notification_api_component import NotificationAPIComponent

_MARK = "components.notification_component.NotificationComponent.mark_unread_notifications_as_read"


@dataclass
class Case:
    id: str


CASES = [
    Case(id="delegates to NotificationComponent.mark_unread_notifications_as_read"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_mark_notifications_as_read(case: Case, mocker):
    mark = mocker.patch(_MARK)

    await NotificationAPIComponent().mark_notifications_as_read()

    mark.assert_awaited_once_with()
