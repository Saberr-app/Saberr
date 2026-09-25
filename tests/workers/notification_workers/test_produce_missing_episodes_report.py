from dataclasses import dataclass

import pytest

from config import config
from components.operational_components.episode_component import EpisodeComponent
from workers.notification_workers import NotificationWorkers


@dataclass
class Case:
    id: str
    webhook_url: str | None
    report_enabled: bool
    expect_sent: bool


CASES = [
    Case(id="sends when webhook is set and report is enabled",
         webhook_url="https://discord.com/api/webhooks/1/abc", report_enabled=True, expect_sent=True),
    Case(id="skips when report is disabled",
         webhook_url="https://discord.com/api/webhooks/1/abc", report_enabled=False, expect_sent=False),
    Case(id="skips when no webhook is configured",
         webhook_url=None, report_enabled=True, expect_sent=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_produce_missing_episodes_report(case: Case, mocker):
    config.user_settings.notifications_discord_webhook_url = case.webhook_url
    config.user_settings.discord_send_daily_missing_report = case.report_enabled
    send_report = mocker.patch.object(EpisodeComponent, "send_tracked_anime_episode_coverage_report")

    await NotificationWorkers.__new__(NotificationWorkers).produce_missing_episodes_report()

    if case.expect_sent:
        send_report.assert_awaited_once_with()
    else:
        send_report.assert_not_awaited()