from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

import pytest

from app_state import global_status
from components.api_components.status_api_component import StatusAPIComponent
from config import config
from constants import NotificationLevel

_NOTIF = "components.notification_component.NotificationComponent"
_DOWNSTREAM = "app_state.downstream_healthcheck_workers.get_statuses_data"
_WHEN = datetime(2024, 1, 1)


def _freeze_timestamps(mocker):
    for attr in ("settings_last_updated", "tracked_anime_last_updated",
                 "anime_list_last_refreshed", "download_last_added"):
        mocker.patch.object(global_status, attr, _WHEN)


@dataclass
class Case:
    id: str
    stale: bool
    expected_count: int
    expected_error_count: int


CASES = [
    Case(id="uses cached counts when not stale", stale=False, expected_count=5, expected_error_count=2),
    Case(id="recomputes counts from unread notifications when stale", stale=True,
         expected_count=3, expected_error_count=1),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_status(case: Case, mocker):
    _freeze_timestamps(mocker)
    mocker.patch.object(global_status, "notification_count_stale", case.stale)
    mocker.patch.object(global_status, "unread_notification_count", 5)
    mocker.patch.object(global_status, "unread_error_notification_count", 2)
    mocker.patch(_DOWNSTREAM, return_value={})

    if case.stale:
        notifications = [SimpleNamespace(level=NotificationLevel.ERROR),
                         SimpleNamespace(level=NotificationLevel.INFO),
                         SimpleNamespace(level=NotificationLevel.INFO)]
        mocker.patch(f"{_NOTIF}.get_notifications", return_value=notifications)

    result = await StatusAPIComponent().get_status()

    assert result.version == config.app_version.original_version_string
    assert result.unread_notification_count == case.expected_count
    assert result.unread_error_notification_count == case.expected_error_count
    assert result.services_status == {}
    if case.stale:
        assert global_status.notification_count_stale is False
