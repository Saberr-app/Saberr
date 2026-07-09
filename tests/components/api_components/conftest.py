import dataclasses
from datetime import datetime, UTC, timedelta
from itertools import count

import pytest

from config import config
from constants import AUDIT_LOG_CODE_TO_CATEGORY_MAP, NotificationStatus
from dto.orm_models import AuditLog, Notification

_ids = count(1)


@pytest.fixture(autouse=True)
def _restore_user_settings():
    """Update endpoints mutate the in-memory `config.user_settings`, so snapshot every field and
    restore it after each test to keep tests isolated."""
    snapshot = {f.name: getattr(config.user_settings, f.name)
                for f in dataclasses.fields(config.user_settings)}
    try:
        yield
    finally:
        for name, value in snapshot.items():
            setattr(config.user_settings, name, value)


@pytest.fixture
def settings_api():
    from components.api_components.settings_api_component import SettingsAPIComponent
    return SettingsAPIComponent()


@pytest.fixture
def make_audit_log():
    """Build an in-memory AuditLog ORM object (no DB)."""
    def _make(*, code, text="audit text", data=None, context_id="ctx", created_at=None):
        audit_log = AuditLog(code=code, category=AUDIT_LOG_CODE_TO_CATEGORY_MAP[code], text=text,
                             data=data if data is not None else {}, context_id=context_id)
        audit_log.id = next(_ids)
        audit_log.created_at = created_at or datetime.now(UTC)
        return audit_log
    return _make


@pytest.fixture
def make_notification():
    """Build an in-memory Notification ORM object (no DB)."""
    def _make(*, code, level, text="notif text", identifier=None,
              status=NotificationStatus.UNREAD, effective_at=None):
        notification = Notification(
            code=code, level=level, text=text, identifier=identifier, status=status,
            effective_at=effective_at or (datetime.now(UTC) - timedelta(minutes=1)))
        notification.id = next(_ids)
        return notification
    return _make
