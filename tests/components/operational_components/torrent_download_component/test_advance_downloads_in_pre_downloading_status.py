from dataclasses import dataclass, field
from unittest.mock import AsyncMock

import pytest

from constants import AuditLogCode, TorrentDownloadStatus as Status

_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"


@dataclass
class Case:
    id: str
    seed_status: Status
    seed_kwargs: dict = field(default_factory=dict)
    qbit_present: bool = False
    qbit_state: str = "uploading"
    qbit_progress: float = 1.0
    add_torrent_succeeds: bool | None = None
    add_torrent_save_path: str = "/dl/final"
    expected_status: Status = Status.DOWNLOADING
    expected_directory_path: str | None = None
    expected_retry_count: int | None = None
    expected_audit_code: AuditLogCode | None = None


CASES = [
    Case(id="init resend success moves to downloading", seed_status=Status.FAILED_DOWNLOAD_INIT,
         qbit_present=False, add_torrent_succeeds=True, add_torrent_save_path="/dl/final",
         expected_status=Status.DOWNLOADING, expected_directory_path="/dl/final", expected_retry_count=0),
    Case(id="init resend failure increments retry", seed_status=Status.FAILED_DOWNLOAD_INIT,
         seed_kwargs=dict(status_retry_count=0), qbit_present=False, add_torrent_succeeds=False,
         expected_status=Status.FAILED_DOWNLOAD_INIT, expected_retry_count=1),
    Case(id="failed download recovered to downloaded", seed_status=Status.FAILED_DOWNLOAD,
         qbit_present=True, qbit_state="uploading", qbit_progress=1.0,
         expected_status=Status.DOWNLOADED, expected_audit_code=AuditLogCode.TORRENT_DOWNLOAD_FINISHED),
    Case(id="still failed in qbit increments retry", seed_status=Status.FAILED_DOWNLOAD,
         seed_kwargs=dict(status_retry_count=1), qbit_present=True, qbit_state="error",
         expected_status=Status.FAILED_DOWNLOAD, expected_retry_count=2),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_advance_downloads_in_pre_downloading_status(case: Case, make_torrent_download_component,
                                                           make_qbit, make_download_chain, mocker):
    download = make_download_chain(status=case.seed_status, **case.seed_kwargs)
    # the method pulls failed/init downloads first, then a second batch of PENDING ones
    mocker.patch(f"{_REPO}.get_downloads", side_effect=[[download], []])
    mocker.patch(f"{_REPO}.get_active_downloads_by_episode_id_and_part", return_value=[])
    repo_update = mocker.patch(f"{_REPO}.update_downloads")

    component = make_torrent_download_component()
    component._qbit_component.get_torrents = AsyncMock(return_value=(
        [make_qbit(hash=download.torrent.magnet_hash, state=case.qbit_state, progress=case.qbit_progress)]
        if case.qbit_present else []))
    if case.add_torrent_succeeds:
        component._qbit_component.add_torrent = AsyncMock(
            return_value=make_qbit(save_path=case.add_torrent_save_path))
    elif case.add_torrent_succeeds is False:
        component._qbit_component.add_torrent = AsyncMock(side_effect=RuntimeError("still down"))

    await component.advance_downloads_in_pre_downloading_status()

    status_updates = [c for c in repo_update.await_args_list
                      if c.kwargs.get("download_ids") == [download.id]]
    assert status_updates
    final = status_updates[-1].kwargs
    assert final["status"] == case.expected_status
    if case.expected_directory_path is not None:
        assert final["download_directory_path"] == case.expected_directory_path
    if case.expected_retry_count is not None:
        assert final["status_retry_count"] == case.expected_retry_count
    if case.expected_audit_code is not None:
        assert component._audit_log_component.log_torrent_processing_action.await_args.kwargs["code"] == \
            case.expected_audit_code
