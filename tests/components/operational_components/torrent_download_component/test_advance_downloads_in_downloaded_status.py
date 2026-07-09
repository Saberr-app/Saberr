from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from constants import AuditLogCode, TorrentDownloadStatus as Status

_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"
_DEST = Path("/library/Show/New.mkv")
_SRC = Path("/downloads/Show/New.mkv")


@dataclass
class Case:
    id: str
    seed_status: Status = Status.DOWNLOADED
    seed_kwargs: dict = field(default_factory=dict)
    qbit_state: str = "uploading"
    qbit_progress: float = 1.0
    processing_succeeds: bool = True
    expected_status: Status = Status.PROCESSING
    expected_destination_path: str | None = None
    expected_returns_task: bool = False
    expected_processing_called: bool = True
    expected_audit_code: AuditLogCode | None = None


CASES = [
    Case(id="downloaded processed successfully moves to processing",
         expected_status=Status.PROCESSING, expected_destination_path=str(_DEST),
         expected_returns_task=True, expected_audit_code=AuditLogCode.TORRENT_PROCESSING_STARTED),
    Case(id="processing failure moves to failed processing", processing_succeeds=False,
         expected_status=Status.FAILED_PROCESSING,
         expected_audit_code=AuditLogCode.TORRENT_PROCESSING_FAILED),
    Case(id="error state moves to failed download without processing", qbit_state="error",
         expected_status=Status.FAILED_DOWNLOAD, expected_processing_called=False,
         expected_audit_code=AuditLogCode.TORRENT_DOWNLOAD_FAILED),
    Case(id="failed processing retry then processes", seed_status=Status.FAILED_PROCESSING,
         seed_kwargs=dict(status_retry_count=0), expected_status=Status.PROCESSING,
         expected_returns_task=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_advance_downloads_in_downloaded_status(case: Case, make_torrent_download_component,
                                                      make_qbit, make_download_chain, mocker):
    download = make_download_chain(status=case.seed_status, **case.seed_kwargs)

    def get_downloads(*, statuses, **kw):
        return [download] if statuses == [case.seed_status] else []

    mocker.patch(f"{_REPO}.get_downloads", side_effect=get_downloads)
    mocker.patch(f"{_REPO}.get_active_downloads_by_episode_id_and_part", return_value=[])
    repo_update = mocker.patch(f"{_REPO}.update_downloads")

    component = make_torrent_download_component()
    component._qbit_component.get_torrents = AsyncMock(return_value=[
        make_qbit(hash=download.torrent.magnet_hash, state=case.qbit_state, progress=case.qbit_progress)])
    task = MagicMock()
    component._processing_component.initiate_download_processing = (
        AsyncMock(return_value=(_DEST, _SRC, task)) if case.processing_succeeds
        else AsyncMock(side_effect=RuntimeError("boom")))

    processing_tasks = await component.advance_downloads_in_downloaded_status()

    status_updates = [c for c in repo_update.await_args_list
                      if c.kwargs.get("download_ids") == [download.id]]
    assert status_updates  # at least one write targeted the download
    final = status_updates[-1].kwargs
    assert final["status"] == case.expected_status
    if case.expected_destination_path is not None:
        assert final["destination_path"] == case.expected_destination_path
    if case.expected_returns_task:
        assert processing_tasks == [task]
    if not case.expected_processing_called:
        assert not component._processing_component.initiate_download_processing.called
    if case.expected_audit_code is not None:
        assert component._audit_log_component.log_torrent_processing_action.await_args.kwargs["code"] == \
            case.expected_audit_code
