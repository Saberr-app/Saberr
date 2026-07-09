from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from constants import AuditLogCode, TorrentDownloadStatus as Status

_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"


@dataclass
class Case:
    id: str
    qbit_present: bool
    qbit_state: str
    qbit_progress: float
    expected: Status | None  # status written, or None when unchanged
    expected_audit_code: AuditLogCode | None


CASES = [
    Case(id="completed-to-downloaded", qbit_present=True, qbit_state="uploading", qbit_progress=1.0,
         expected=Status.DOWNLOADED, expected_audit_code=AuditLogCode.TORRENT_DOWNLOAD_FINISHED),
    Case(id="error-to-failed-download", qbit_present=True, qbit_state="error", qbit_progress=1.0,
         expected=Status.FAILED_DOWNLOAD, expected_audit_code=AuditLogCode.TORRENT_DOWNLOAD_FAILED),
    Case(id="still-downloading-unchanged", qbit_present=True, qbit_state="downloading", qbit_progress=0.5,
         expected=None, expected_audit_code=None),
    Case(id="missing-in-qbit-marks-deleted", qbit_present=False, qbit_state="uploading", qbit_progress=1.0,
         expected=Status.DELETED, expected_audit_code=AuditLogCode.TORRENT_DOWNLOAD_DELETED),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_advance_downloads_in_downloading_status(case: Case, make_torrent_download_component,
                                                       make_qbit, make_download_chain, mocker):
    download = make_download_chain(status=Status.DOWNLOADING)
    mocker.patch(f"{_REPO}.get_downloads", return_value=[download])
    mocker.patch(f"{_REPO}.get_active_downloads_by_episode_id_and_part", return_value=[])  # not superseded
    repo_update = mocker.patch(f"{_REPO}.update_downloads")

    component = make_torrent_download_component()
    component._qbit_component.get_torrents = AsyncMock(return_value=(
        [make_qbit(hash=download.torrent.magnet_hash, state=case.qbit_state, progress=case.qbit_progress)]
        if case.qbit_present else []))

    await component.advance_downloads_in_downloading_status()

    status_updates = [c for c in repo_update.await_args_list
                      if c.kwargs.get("download_ids") == [download.id]]
    if case.expected is None:
        assert status_updates == []  # only the (empty) superseded-discard update ran
    else:
        assert len(status_updates) == 1
        assert status_updates[0].kwargs["status"] == case.expected

    audit = component._audit_log_component.log_torrent_processing_action
    if case.expected_audit_code is None:
        audit.assert_not_awaited()
    else:
        assert audit.await_args.kwargs["code"] == case.expected_audit_code
