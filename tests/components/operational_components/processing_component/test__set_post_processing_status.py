from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from components.operational_components import processing_component
from constants import AuditLogCode, TorrentDownloadStatus as Status

_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"


@dataclass
class Case:
    id: str
    succeeded: bool
    error: Exception | None
    expected_status: Status
    expected_audit: AuditLogCode
    expected_details: str | None
    expected_filter: list


CASES = [
    Case(id="success marks downloads processed and audits completion",
         succeeded=True, error=None,
         expected_status=Status.PROCESSED, expected_audit=AuditLogCode.TORRENT_PROCESSING_FINISHED,
         expected_details=None, expected_filter=[]),
    # failure only touches rows still in PROCESSING and records the error detail
    Case(id="failure marks downloads failed and audits failure",
         succeeded=False, error=Exception("boom"),
         expected_status=Status.FAILED_PROCESSING, expected_audit=AuditLogCode.TORRENT_PROCESSING_FAILED,
         expected_details="Failed to copy video file to destination: boom",
         expected_filter=[Status.PROCESSING]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test__set_post_processing_status(case: Case, make_processing_component, mocker):
    downloads = [SimpleNamespace(id=1, torrent="t1"), SimpleNamespace(id=2, torrent="t2")]
    mocker.patch(f"{_REPO}.get_downloads", return_value=downloads)
    update = mocker.patch(f"{_REPO}.update_downloads")
    global_status = mocker.patch.object(processing_component, "global_status")
    component = make_processing_component()

    await component._set_post_processing_status(succeeded=case.succeeded, torrent_download_ids=[1, 2],
                                                error=case.error)

    kwargs = update.await_args.kwargs
    assert kwargs["download_ids"] == [1, 2]
    assert kwargs["status"] == case.expected_status
    assert kwargs["status_details"] == case.expected_details
    assert kwargs["filter_by_statuses"] == case.expected_filter
    # a copy timestamp is stamped on success only
    assert (kwargs["copied_to_destination_path_at"] is not None) is case.succeeded

    audit = component._audit_log_component.log_torrent_processing_action
    audit.assert_awaited_once()
    assert audit.await_args.kwargs["code"] == case.expected_audit
    assert audit.await_args.kwargs["torrent_download"] is downloads[0]
    assert audit.await_args.kwargs["db_torrents"] == ["t1", "t2"]
    global_status.tracked_anime_updated.assert_called_once()
