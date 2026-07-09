from dataclasses import dataclass

import pytest

from constants import TorrentDownloadStatus

_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"


@dataclass
class Case:
    id: str
    status: TorrentDownloadStatus
    download_directory_path: str
    destination_path: str
    status_details: str


CASES = [
    Case(id="delegates to repo.create_download with given fields", status=TorrentDownloadStatus.PENDING,
         download_directory_path="/staging", destination_path="/dest/file.mkv", status_details="note"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_create_download(case: Case, make_torrent_download_component, make_torrent_download, mocker):
    created = make_torrent_download(torrent_id=7, status=case.status,
                                    download_directory_path=case.download_directory_path,
                                    destination_path=case.destination_path,
                                    status_details=case.status_details)
    repo_create = mocker.patch(f"{_REPO}.create_download", return_value=created)

    result = await make_torrent_download_component().create_download(
        torrent_id=7, status=case.status, download_directory_path=case.download_directory_path,
        destination_path=case.destination_path, status_details=case.status_details)

    assert result is created
    repo_create.assert_awaited_once_with(
        torrent_id=7, status=case.status, status_retry_count=0, status_details=case.status_details,
        download_directory_path=case.download_directory_path, destination_path=case.destination_path,
        copied_to_destination_path_at=None)
