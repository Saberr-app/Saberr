from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Callable

import pytest

from config import config
from constants import NotificationLevel
from utils.helpers.discord_webhook_helpers import construct_discord_webhook_payload_for_notification

_WHEN = datetime(2021, 1, 1, tzinfo=UTC)
_PUBLISHED_URL = "https://dash.test"


def build(notification_id=1, description="desc",
          level: NotificationLevel | None = NotificationLevel.INFO, fields=None, title="Title", time=_WHEN):
    return construct_discord_webhook_payload_for_notification(
        notification_id, description, level, fields or [], title, time)


@dataclass
class Case:
    id: str
    kwargs: dict = field(default_factory=dict)
    check: Callable[[dict], None] | None = None
    expected_exception: type[Exception] | None = None


def _check_color(color):
    def check(payload):
        assert payload["embeds"][0]["color"] == color
    return check


def _check_dashboard_field(payload):
    last_field = payload["embeds"][0]["fields"][-1]
    assert last_field["name"] == "Saberr"
    assert "notification_id=42" in last_field["value"]


def _check_user_fields(payload):
    result = payload["embeds"][0]["fields"]
    assert result[0] == {"name": "A", "value": "1", "inline": False}
    assert all(f["inline"] is False for f in result)


def _check_timestamp(payload):
    # Discord embed timestamps are ISO-8601 strings, not unix ints
    assert payload["embeds"][0]["timestamp"] == _WHEN.isoformat()


def _check_long_title(payload):
    title = payload["embeds"][0]["title"]
    assert len(title) == 250 and title.endswith("...")


CASES = [
    Case(id="color INFO", kwargs=dict(level=NotificationLevel.INFO), check=_check_color(0x4971A0)),
    Case(id="color WARNING", kwargs=dict(level=NotificationLevel.WARNING), check=_check_color(0xD65F45)),
    Case(id="color ERROR", kwargs=dict(level=NotificationLevel.ERROR), check=_check_color(0xB63030)),
    # regression: invalid level used to be a bare `raise` -> confusing RuntimeError
    Case(id="invalid level raises", kwargs=dict(level=None), expected_exception=ValueError),
    Case(id="appends dashboard field", kwargs=dict(notification_id=42), check=_check_dashboard_field),
    Case(id="user fields are preserved",
         kwargs=dict(fields=[{"name": "A", "value": "1"}, {"name": "B", "value": "2"}]),
         check=_check_user_fields),
    Case(id="timestamp is iso8601", kwargs=dict(time=_WHEN), check=_check_timestamp),
    Case(id="long title is shortened", kwargs=dict(title="T" * 300), check=_check_long_title),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_construct_discord_webhook_payload_for_notification(case: Case):
    config.user_settings.published_url = _PUBLISHED_URL  # enables the dashboard-link field
    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            build(**case.kwargs)
        return
    case.check(build(**case.kwargs))
