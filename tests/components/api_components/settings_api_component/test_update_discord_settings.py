from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from config import config
from api.schemas.settings_schemas import DiscordSettings


@dataclass
class Case:
    id: str
    body: DiscordSettings
    expected_discord_user_id: str
    expected_releases_url: str | None


CASES = [
    Case(id="persists and returns discord section",
         body=DiscordSettings(
             notifications_discord_webhook_url=None,
             discord_webhook_username=None,
             discord_webhook_avatar_url=None,
             discord_user_id="123456789",
             discord_notify_on_login=False,
             discord_notify_on_download_processed=True,
             discord_notify_on_upgrade_download_processed=True,
             discord_notify_on_download_failed=True,
         ),
         expected_discord_user_id="123456789",
         expected_releases_url=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_discord_settings(case: Case, bound_session, settings_api, monkeypatch):
    # the update triggers real Discord webhook healthchecks; stub them out so no network call happens.
    from app_state import downstream_healthcheck_workers
    monkeypatch.setattr(downstream_healthcheck_workers, "_check_notifications_discord_webhook", AsyncMock())

    result = await settings_api.update_discord_settings(case.body)

    assert config.user_settings.discord_user_id == case.expected_discord_user_id
    assert result.discord_user_id == case.expected_discord_user_id
