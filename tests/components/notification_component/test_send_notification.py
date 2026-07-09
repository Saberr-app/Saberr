from dataclasses import dataclass

import pytest

from components.notification_component import NotificationComponent
from constants import NotificationCode, NotificationLevel, NotificationStatus


@dataclass
class Case:
    id: str
    text: str
    level: NotificationLevel
    identifier: dict | None
    status: NotificationStatus
    send_discord_notification: bool
    expected_discord_sent: bool


CASES = [
    Case(id="creates a row, no discord when not requested",
         text="hello", level=NotificationLevel.INFO, identifier={"a": 1},
         status=NotificationStatus.UNREAD, send_discord_notification=False,
         expected_discord_sent=False),
    Case(id="no discord for a non-unread status",
         text="seen", level=NotificationLevel.INFO, identifier=None,
         status=NotificationStatus.READ, send_discord_notification=True,
         expected_discord_sent=False),
    Case(id="sends discord when requested and unread",
         text="ping", level=NotificationLevel.WARNING, identifier=None,
         status=NotificationStatus.UNREAD, send_discord_notification=True,
         expected_discord_sent=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_send_notification(case: Case, make_notification, mocker):
    # configured webhook url so the discord branch is reachable; the external send is mocked.
    from config import config
    config.user_settings.notifications_discord_webhook_url = "https://discord.test/notifs"
    created = make_notification(code=NotificationCode.LOGIN, level=case.level, text=case.text,
                                identifier=case.identifier, status=case.status)
    repo_create = mocker.patch(
        "repositories.notification_repo.NotificationRepo.create_notification", return_value=created)
    discord = mocker.patch.object(NotificationComponent, "_send_discord_notification")

    await NotificationComponent().send_notification(
        code=NotificationCode.LOGIN, level=case.level, text=case.text,
        identifier=case.identifier, status=case.status,
        send_discord_notification=case.send_discord_notification)

    repo_create.assert_awaited_once()
    passed = repo_create.await_args.kwargs
    assert passed["code"] is NotificationCode.LOGIN
    assert passed["level"] is case.level
    assert passed["text"] == case.text
    assert passed["identifier"] == case.identifier
    assert passed["status"] is case.status

    assert discord.await_count == (1 if case.expected_discord_sent else 0)
