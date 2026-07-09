from dataclasses import dataclass

import pytest

from config import config
from constants import AuditLogCode, TorrentDownloadStatus as Status

_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"


@dataclass
class Case:
    id: str
    status: Status            # status the stuck download currently sits in
    stuck: bool               # whether the repo's age filter returns it
    expected_new_status: Status | None
    expected_audit_code: AuditLogCode | None = None


CASES = [
    Case(id="downloading-to-failed-download", status=Status.DOWNLOADING, stuck=True,
         expected_new_status=Status.FAILED_DOWNLOAD,
         expected_audit_code=AuditLogCode.TORRENT_DOWNLOAD_FAILED),
    Case(id="processing-to-failed-processing", status=Status.PROCESSING, stuck=True,
         expected_new_status=Status.FAILED_PROCESSING,
         expected_audit_code=AuditLogCode.TORRENT_PROCESSING_FAILED),
    Case(id="recent-downloading-left-alone", status=Status.DOWNLOADING, stuck=False,
         expected_new_status=None),
    Case(id="recent-processing-left-alone", status=Status.PROCESSING, stuck=False,
         expected_new_status=None),
]


@pytest.fixture(autouse=True)
def stuck_thresholds():
    config.user_settings.set_download_as_failed_after_minutes = 60
    config.user_settings.set_processing_as_failed_after_minutes = 60


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_mark_stuck_downloads_as_failed(case: Case, make_torrent_download_component,
                                              make_download_chain, mocker):
    download = make_download_chain(status=case.status)

    # The repo applies the age filter; simulate it returning the download only when "stuck".
    def get_downloads(*, statuses, **kw):
        return [download] if case.stuck and statuses == [case.status] else []

    mocker.patch(f"{_REPO}.get_downloads", side_effect=get_downloads)
    repo_update = mocker.patch(f"{_REPO}.update_downloads")

    component = make_torrent_download_component()
    await component.mark_stuck_downloads_as_failed()

    updated_with_target = [c for c in repo_update.await_args_list
                           if c.kwargs.get("download_ids") == [download.id]]
    if case.expected_new_status is None:
        assert updated_with_target == []
        component._audit_log_component.log_torrent_processing_action.assert_not_awaited()
    else:
        assert len(updated_with_target) == 1
        assert updated_with_target[0].kwargs["status"] == case.expected_new_status
        assert component._audit_log_component.log_torrent_processing_action.await_args.kwargs["code"] == \
            case.expected_audit_code
