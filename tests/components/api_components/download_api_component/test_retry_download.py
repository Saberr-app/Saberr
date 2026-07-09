from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from common.exceptions import NotFoundException, ValidationException
from components.api_components.download_api_component import DownloadAPIComponent
from constants import TorrentDownloadStatus as Status

_DC = "components.operational_components.torrent_download_component.TorrentDownloadComponent"
_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"


def _download(status):
    return SimpleNamespace(id=1, status=status, torrent=SimpleNamespace(magnet_hash="h"))


def _sibling():
    return SimpleNamespace(id=1, status_retry_count=2, download_directory_path="/dl",
                           torrent=SimpleNamespace(magnet_hash="h", torrent_link="link"))


@dataclass
class Case:
    id: str
    seed_status: Status | None
    qbit_succeeds: bool = True
    expected_status: Status | None = None
    expected_retry_count: int | None = None
    expected_directory_path: str | None = None
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="missing download raises not found",
         seed_status=None, expected_exception=NotFoundException),
    Case(id="non-retryable status is rejected",
         seed_status=Status.PROCESSED, expected_exception=ValidationException),
    # a failed download resent successfully lands in DOWNLOADING with reset retry count
    Case(id="successful resend moves to downloading",
         seed_status=Status.FAILED_DOWNLOAD, qbit_succeeds=True,
         expected_status=Status.DOWNLOADING, expected_retry_count=0, expected_directory_path="/final"),
    # a failing resend bumps the retry count and flags init failure
    Case(id="failed resend increments retry",
         seed_status=Status.FAILED_DOWNLOAD, qbit_succeeds=False,
         expected_status=Status.FAILED_DOWNLOAD_INIT, expected_retry_count=3),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_retry_download(case: Case, mocker):
    download = _download(case.seed_status) if case.seed_status is not None else None
    mocker.patch(f"{_DC}.get_download", return_value=download)
    mocker.patch(f"{_DC}.get_downloads_by_hashes", return_value=[_sibling()])
    mocker.patch(f"{_DC}.get_torrent_tags_and_category", return_value=(["tag"], "cat"))
    update = mocker.patch(f"{_REPO}.update_downloads")

    component = DownloadAPIComponent()
    component.logger = mocker.MagicMock()  # used only on the qbit-failure log path
    if case.qbit_succeeds:
        component._download_component.send_download_to_qbit = AsyncMock(
            return_value=SimpleNamespace(save_path="/final"))
    else:
        component._download_component.send_download_to_qbit = AsyncMock(side_effect=RuntimeError("down"))

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await component.retry_download(download_id=1)
        update.assert_not_awaited()
        return

    await component.retry_download(download_id=1)

    # the first update sets PENDING; the final one records the qbit outcome
    final = update.await_args_list[-1].kwargs
    assert final["download_ids"] == [1]
    assert final["status"] == case.expected_status
    assert final["status_retry_count"] == case.expected_retry_count
    if case.expected_directory_path is not None:
        assert final["download_directory_path"] == case.expected_directory_path
