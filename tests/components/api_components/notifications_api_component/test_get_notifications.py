from dataclasses import dataclass, field

import pytest

from components.api_components.notification_api_component import NotificationAPIComponent
from constants import NotificationCode, NotificationLevel, NotificationStatus, SortDirection
from api.schemas.notification_schemas import NotificationListRequest

LEVEL = list(NotificationLevel)[0]


@dataclass
class Case:
    id: str
    request_factory: object = field(default_factory=lambda: NotificationListRequest)
    expected_forwarded: dict = field(default_factory=dict)
    assert_mapped: bool = False


CASES = [
    Case(id="forwards defaults and maps items",
         request_factory=NotificationListRequest, assert_mapped=True),
    Case(id="forwards status filter",
         request_factory=lambda: NotificationListRequest(statuses=[NotificationStatus.READ]),
         expected_forwarded={"statuses": [NotificationStatus.READ]}),
    Case(id="forwards sort direction",
         request_factory=lambda: NotificationListRequest(sort_direction=SortDirection.ASC),
         expected_forwarded={"sort_direction": SortDirection.ASC}),
    Case(id="forwards limit and offset",
         request_factory=lambda: NotificationListRequest(offset=1, limit=1),
         expected_forwarded={"offset": 1, "limit": 1}),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_notifications(case: Case, make_notification, mocker):
    notification = make_notification(code=NotificationCode.LOGIN, level=LEVEL, text="first",
                                     identifier={"k": "v"}, status=NotificationStatus.UNREAD)
    component_get = mocker.patch(
        "components.notification_component.NotificationComponent.get_notifications",
        return_value=[notification])

    result = await NotificationAPIComponent().get_notifications(params=case.request_factory())

    forwarded = component_get.await_args.kwargs
    for key, value in case.expected_forwarded.items():
        assert forwarded[key] == value

    if case.assert_mapped:
        item = result.notifications[0]
        assert item.id == notification.id
        assert item.code is NotificationCode.LOGIN
        assert item.status is NotificationStatus.UNREAD
        assert item.identifier == {"k": "v"}
