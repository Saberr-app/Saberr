from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from api.schemas.download_schemas import DeleteDownloadRequest
from common.exceptions import NotFoundException
from components.api_components.download_api_component import DownloadAPIComponent
from constants import TorrentDownloadStatus as Status

_DC = "components.operational_components.torrent_download_component.TorrentDownloadComponent"

_BODY = DeleteDownloadRequest(delete_from_qbit=True, delete_from_disk=True,
                              delete_imported_file=False, discard_torrent=False)


def _download(status):
    return SimpleNamespace(id=1, status=status, torrent=SimpleNamespace(magnet_hash="h1"))


@dataclass
class Case:
    id: str
    download: object
    expected_exception: type[Exception] | None = None
    expected_delete: bool = False


CASES = [
    Case(id="missing download raises not found", download=None, expected_exception=NotFoundException),
    # deletion is no longer gated on status; the body flags decide what gets cleaned up
    Case(id="processed download can be deleted",
         download=_download(Status.PROCESSED), expected_delete=True),
    Case(id="deletable download is removed everywhere",
         download=_download(Status.FAILED_DOWNLOAD), expected_delete=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_delete_download(case: Case, mocker):
    mocker.patch(f"{_DC}.get_download", return_value=case.download)
    delete = mocker.patch(f"{_DC}.delete_downloads_by_magnet_hashes")

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await DownloadAPIComponent().delete_download(download_id=1, body=_BODY)
        delete.assert_not_awaited()
        return

    await DownloadAPIComponent().delete_download(download_id=1, body=_BODY)
    if case.expected_delete:
        delete.assert_awaited_once_with(magnet_hashes=["h1"], delete_from_qbit=True, delete_from_disk=True)
