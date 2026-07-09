from datetime import datetime, UTC, timedelta

import pytest

from constants import NotificationStatus
from dto.orm_models import Notification


@pytest.fixture
def make_notification():
    """Build an in-memory Notification ORM object (no DB). `default=` doesn't fire pre-flush, so every
    field the code reads is set explicitly."""
    _id = {"next": 1}

    def _make(*, code, level, text="notif", identifier=None,
              status=NotificationStatus.UNREAD, effective_at=None, notification_id=None):
        notification = Notification(
            code=code, level=level, text=text, identifier=identifier, status=status,
            # default effective_at in the past so a default `effective_before=now` would include it.
            effective_at=effective_at or (datetime.now(UTC) - timedelta(minutes=1)),
        )
        notification.id = notification_id if notification_id is not None else _id["next"]
        _id["next"] += 1
        return notification

    return _make
