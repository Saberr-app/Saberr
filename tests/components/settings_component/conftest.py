import dataclasses

import pytest

from config import config


@pytest.fixture(autouse=True)
def _restore_user_settings():
    """update_* mutate the in-memory config.user_settings (not rolled back with the DB);
    snapshot and restore every field after each test."""
    snapshot = {f.name: getattr(config.user_settings, f.name)
                for f in dataclasses.fields(config.user_settings)}
    try:
        yield
    finally:
        for name, value in snapshot.items():
            setattr(config.user_settings, name, value)
