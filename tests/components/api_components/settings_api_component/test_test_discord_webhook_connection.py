from dataclasses import dataclass

import pytest

from components.api_components.settings_api_component import SettingsAPIComponent
from api.schemas.settings_schemas import DiscordWebhookTest

_SERVICE = "services.discord_webhook_service.DiscordWebhookService"


@dataclass
class Case:
    id: str
    webhook_url: str


CASES = [
    Case(id="forwards the webhook url to the service healthcheck",
         webhook_url="http://hook.example/abc"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_test_discord_webhook_connection(case: Case, mocker):
    healthcheck = mocker.patch(f"{_SERVICE}.healthcheck")

    await SettingsAPIComponent().test_discord_webhook_connection(
        body=DiscordWebhookTest(webhook_url=case.webhook_url))

    healthcheck.assert_awaited_once_with(case.webhook_url)
