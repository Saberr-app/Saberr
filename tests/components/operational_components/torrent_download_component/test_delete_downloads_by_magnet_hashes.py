from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"


@dataclass
class Case:
    id: str
    delete_from_qbit: bool
    delete_from_disk: bool
    expected_qbit_called: bool


CASES = [
    Case(id="db only by default", delete_from_qbit=False, delete_from_disk=False, expected_qbit_called=False),
    Case(id="also removes from qbit when requested", delete_from_qbit=True, delete_from_disk=True,
         expected_qbit_called=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_delete_downloads_by_magnet_hashes(case: Case, make_torrent_download_component, mocker):
    repo = mocker.patch(f"{_REPO}.delete_downloads_by_magnet_hashes")
    component = make_torrent_download_component()
    component._qbit_component.delete_torrents = AsyncMock()
    hashes = ["h1", "h2"]

    await component.delete_downloads_by_magnet_hashes(magnet_hashes=hashes,
                                                      delete_from_qbit=case.delete_from_qbit,
                                                      delete_from_disk=case.delete_from_disk)

    repo.assert_awaited_once_with(magnet_hashes=hashes)
    if case.expected_qbit_called:
        component._qbit_component.delete_torrents.assert_awaited_once_with(
            magnet_hashes=hashes, delete_from_disk=case.delete_from_disk)
    else:
        component._qbit_component.delete_torrents.assert_not_awaited()
