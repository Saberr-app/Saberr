from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from config import config
from constants import AuditLogCode, TorrentDownloadStatus as Status

_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"


@dataclass
class Case:
    id: str
    qbit_succeeds: bool
    expected_status: Status
    expected_audit_code: AuditLogCode
    expected_directory_path: str | None = None


CASES = [
    Case(id="success creates a downloading row with the qbit save_path", qbit_succeeds=True,
         expected_status=Status.DOWNLOADING, expected_audit_code=AuditLogCode.TORRENT_DOWNLOAD_STARTED,
         expected_directory_path="/dl/final"),
    Case(id="qbit failure marks failed download init", qbit_succeeds=False,
         expected_status=Status.FAILED_DOWNLOAD_INIT,
         expected_audit_code=AuditLogCode.TORRENT_DOWNLOAD_FAILED),
]


@pytest.fixture(autouse=True)
def tags_disabled():
    for flag in ("apply_anime_title_as_torrent_tag", "apply_release_group_as_torrent_tag",
                 "apply_encoding_as_torrent_tag", "apply_resolution_as_torrent_tag",
                 "apply_language_code_as_torrent_tag"):
        setattr(config.user_settings, flag, False)
    config.user_settings.torrent_category = ""


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_create_downloads_for_torrent(case: Case, make_torrent_download_component, make_qbit,
                                            make_torrent, make_torrent_download, mocker):
    parent = make_torrent(tracked_anime_episode_id=1)
    child = make_torrent(tracked_anime_episode_id=2, parent_torrent_id=parent.id)
    group = [parent, child]
    repo_create = mocker.patch(
        f"{_REPO}.create_download",
        side_effect=lambda **kw: make_torrent_download(torrent_id=kw["torrent_id"], status=Status.PENDING))
    repo_update = mocker.patch(f"{_REPO}.update_downloads")

    component = make_torrent_download_component()
    component._qbit_component.add_torrent = (
        AsyncMock(return_value=make_qbit(save_path="/dl/final")) if case.qbit_succeeds
        else AsyncMock(side_effect=RuntimeError("qbit down")))

    download = await component.create_downloads_for_torrent(db_torrent_group=group,
                                                            download_directory_path="/staging")

    # a single download is created for the parent torrent only
    assert repo_create.await_count == 1
    assert repo_create.await_args.kwargs["torrent_id"] == parent.id
    assert download.torrent_id == parent.id

    # the status update targets the created download
    update = repo_update.await_args
    assert update.kwargs["download_ids"] == [download.id]
    assert update.kwargs["status"] == case.expected_status
    if case.expected_directory_path is not None:
        assert update.kwargs["download_directory_path"] == case.expected_directory_path

    # the selected action is always logged with the whole group; the processing action carries the code
    component._audit_log_component.log_torrent_selected_action.assert_awaited_once_with(
        db_torrents=group, download_directory_path="/staging")
    audit = component._audit_log_component.log_torrent_processing_action.await_args
    assert audit.kwargs["code"] == case.expected_audit_code
    assert audit.kwargs["torrent_download"] is download
    assert audit.kwargs["db_torrents"] == group
