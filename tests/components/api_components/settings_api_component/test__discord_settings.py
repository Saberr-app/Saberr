from dataclasses import dataclass, field

import pytest

from components.api_components.settings_api_component import SettingsAPIComponent
from tests.support.builders import make_user_settings


@dataclass
class Case:
    id: str
    overrides: dict = field(default_factory=dict)


CASES = [
    Case(id="maps discord fields from user settings",
         overrides=dict(notifications_discord_webhook_url="http://hook",
                        discord_notify_on_login=True, discord_user_id="123")),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__discord_settings(case: Case):
    user_settings = make_user_settings(**case.overrides)
    component = SettingsAPIComponent.__new__(SettingsAPIComponent)

    section = component._discord_settings(user_settings)

    assert section.notifications_discord_webhook_url == user_settings.notifications_discord_webhook_url
    assert section.discord_notify_on_login == user_settings.discord_notify_on_login
    assert section.discord_user_id == user_settings.discord_user_id
    assert section.discord_notify_on_download_processed == user_settings.discord_notify_on_download_processed
    assert section.discord_notify_on_download_failed == user_settings.discord_notify_on_download_failed
