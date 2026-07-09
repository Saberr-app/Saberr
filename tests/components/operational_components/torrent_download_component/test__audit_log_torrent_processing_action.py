from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from constants import AuditLogCode, TorrentDownloadStatus as Status


@dataclass
class Case:
    id: str
    download_status: Status
    only_audit_statuses: list[Status] | None = None
    expected_code: AuditLogCode | None = None  # None => no audit call expected


CASES = [
    Case(id="downloading", download_status=Status.DOWNLOADING,
         expected_code=AuditLogCode.TORRENT_DOWNLOAD_STARTED),
    Case(id="downloaded", download_status=Status.DOWNLOADED,
         expected_code=AuditLogCode.TORRENT_DOWNLOAD_FINISHED),
    Case(id="failed-download", download_status=Status.FAILED_DOWNLOAD,
         expected_code=AuditLogCode.TORRENT_DOWNLOAD_FAILED),
    Case(id="failed-download-init", download_status=Status.FAILED_DOWNLOAD_INIT,
         expected_code=AuditLogCode.TORRENT_DOWNLOAD_FAILED),
    Case(id="discarded", download_status=Status.DISCARDED,
         expected_code=AuditLogCode.TORRENT_DOWNLOAD_DISCARDED),
    Case(id="deleted", download_status=Status.DELETED,
         expected_code=AuditLogCode.TORRENT_DOWNLOAD_DELETED),
    Case(id="processing", download_status=Status.PROCESSING,
         expected_code=AuditLogCode.TORRENT_PROCESSING_STARTED),
    Case(id="failed-processing", download_status=Status.FAILED_PROCESSING,
         expected_code=AuditLogCode.TORRENT_PROCESSING_FAILED),
    Case(id="no-audit-when-status-not-in-allowed-list", download_status=Status.DOWNLOADING,
         only_audit_statuses=[Status.DELETED, Status.FAILED_DOWNLOAD], expected_code=None),
    Case(id="audits-when-status-in-allowed-list", download_status=Status.FAILED_DOWNLOAD,
         only_audit_statuses=[Status.DELETED, Status.FAILED_DOWNLOAD],
         expected_code=AuditLogCode.TORRENT_DOWNLOAD_FAILED),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test__audit_log_torrent_processing_action(case: Case, make_torrent_download_component):
    component = make_torrent_download_component()
    download, torrents = MagicMock(), [MagicMock()]

    kwargs = {}
    if case.only_audit_statuses is not None:
        kwargs["only_audit_statuses"] = case.only_audit_statuses
    await component._audit_log_torrent_processing_action(
        download_status=case.download_status, torrent_download=download, db_torrents=torrents, **kwargs)

    audit = component._audit_log_component.log_torrent_processing_action
    if case.expected_code is None:
        audit.assert_not_awaited()
    else:
        audit.assert_awaited_once_with(
            code=case.expected_code, torrent_download=download, db_torrents=torrents)
