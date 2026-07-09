from dataclasses import dataclass
from datetime import datetime

import pytest

from components.api_components.status_api_component import StatusAPIComponent
from config import config
from api.schemas.status_schemas import Status
from constants import AppContext


def _status(unread_notification_count: int, unread_error_notification_count: int) -> Status:
    return Status(version="9.9.9", ui_minimum_version="8.8.8",
                  unread_notification_count=unread_notification_count,
                  unread_error_notification_count=unread_error_notification_count,
                  settings_last_updated_at=datetime(2024, 1, 1), tracked_anime_last_updated_at=datetime(2024, 1, 1),
                  anime_list_last_refreshed_at=datetime(2024, 1, 1), download_last_added_at=datetime(2024, 1, 1),
                  services_status={}, context=AppContext.WINDOWS, remote_update_available=False)


@dataclass
class Case:
    id: str
    ref: int
    unread_notification_count: int
    unread_error_notification_count: int


CASES = [
    Case(id="counts forwarded from status", ref=7, unread_notification_count=4, unread_error_notification_count=1),
    Case(id="zero counts", ref=1, unread_notification_count=0, unread_error_notification_count=0),
    Case(id="all notifications are errors", ref=99, unread_notification_count=3, unread_error_notification_count=3),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_status_stream_data(case: Case, mocker):
    mocker.patch("components.api_components.status_api_component.StatusAPIComponent.get_status",
                 return_value=_status(case.unread_notification_count, case.unread_error_notification_count))

    stream = await StatusAPIComponent().get_status_stream_data(ref=case.ref)

    assert stream.ref == case.ref
    assert stream.ver == config.app_version.original_version_string
    assert stream.ui_min_ver == config.ui_minimum_version.original_version_string
    assert stream.notif == case.unread_notification_count
    assert stream.err_notif == case.unread_error_notification_count
