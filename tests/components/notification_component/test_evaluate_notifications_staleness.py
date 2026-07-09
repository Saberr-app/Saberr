from dataclasses import dataclass, field

import pytest

from components.notification_component import NotificationComponent
from constants import NotificationCode, NotificationLevel, NotificationStatus


@dataclass
class Case:
    id: str
    code: NotificationCode
    level: NotificationLevel
    identifier: dict = field(default_factory=dict)
    download_found: bool = False
    expected_marked_stale: bool = False


CASES = [
    Case(id="marks stale when referenced download is gone",
         code=NotificationCode.DOWNLOAD_PROCESSING_PERMANENTLY_FAILED, level=NotificationLevel.ERROR,
         identifier={"torrent_download_id": 999999, "status": "FAILED_DOWNLOAD"},
         download_found=False, expected_marked_stale=True),
    Case(id="ignores unrelated codes",
         code=NotificationCode.LOGIN, level=NotificationLevel.INFO, identifier={"whatever": 1},
         download_found=False, expected_marked_stale=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_evaluate_notifications_staleness(case: Case, make_notification, mocker):
    notification = make_notification(
        code=case.code, level=case.level, identifier=case.identifier,
        status=NotificationStatus.UNREAD, notification_id=55)
    mocker.patch("repositories.notification_repo.NotificationRepo.get_notifications",
                 return_value=[notification])
    mocker.patch("repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo.get_download",
                 return_value=None)
    repo_update = mocker.patch(
        "repositories.notification_repo.NotificationRepo.update_notification")

    await NotificationComponent().evaluate_notifications_staleness()

    if case.expected_marked_stale:
        repo_update.assert_awaited_once_with(
            notification_id=55, status=NotificationStatus.STALE)
    else:
        repo_update.assert_not_awaited()
