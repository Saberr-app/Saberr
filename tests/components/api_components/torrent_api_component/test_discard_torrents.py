from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.schemas.torrent_schemas import TorrentDiscardRequest
from common.exceptions import ValidationException
from components.api_components.torrent_api_component import TorrentAPIComponent
from components.operational_components.torrent_component import TorrentComponent
from constants import TorrentDownloadStatus

_BY_HASHES = "components.operational_components.torrent_component.TorrentComponent.get_torrents_by_hashes"
_UPDATE_BY_HASHES = "repositories.torrent_repositories.torrent_repo.TorrentRepo.update_torrents_by_magnet_hashes"
_UPDATE_DOWNLOADS = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo.update_downloads"


def _component() -> TorrentAPIComponent:
    component = TorrentAPIComponent.__new__(TorrentAPIComponent)
    component._torrent_component = TorrentComponent.__new__(TorrentComponent)
    return component


def _torrent(magnet_hash: str, download_status: TorrentDownloadStatus | None, download_id: int = 0):
    # `effective_download` is a computed property on the real ORM, so a stand-in carries just what's read.
    effective_download = SimpleNamespace(id=download_id, status=download_status) if download_status else None
    return SimpleNamespace(magnet_hash=magnet_hash, effective_download=effective_download)


@dataclass
class Case:
    id: str
    torrents: list = field(default_factory=list)
    expected_discarded_download_ids: set | None = None  # None => update_downloads must not be called
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="torrent without a download is only flagged discarded",
         torrents=[_torrent("hashA", None)], expected_discarded_download_ids=None),
    Case(id="pending download is discarded too",
         torrents=[_torrent("hashA", TorrentDownloadStatus.PENDING, download_id=7)],
         expected_discarded_download_ids={7}),
    Case(id="already-processed torrent cannot be discarded",
         torrents=[_torrent("hashA", TorrentDownloadStatus.PROCESSED, download_id=7)],
         expected_exception=ValidationException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_discard_torrents(case: Case, mocker):
    mocker.patch(_BY_HASHES, new_callable=AsyncMock, return_value=case.torrents)
    update_by_hashes = mocker.patch(_UPDATE_BY_HASHES, new_callable=AsyncMock)
    update_downloads = mocker.patch(_UPDATE_DOWNLOADS, new_callable=AsyncMock)
    body = TorrentDiscardRequest(magnet_hashes=["hashA"])

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await _component().discard_torrents(body)
        update_by_hashes.assert_not_called()
        return

    result = await _component().discard_torrents(body)

    assert result is None
    update_by_hashes.assert_awaited_once_with(magnet_hashes=["hashA"], discarded=True)
    if case.expected_discarded_download_ids is None:
        update_downloads.assert_not_called()
    else:
        update_downloads.assert_awaited_once_with(download_ids=case.expected_discarded_download_ids,
                                                  status=TorrentDownloadStatus.DISCARDED)
