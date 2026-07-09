from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from common.exceptions import ExternalServiceException


@dataclass
class Case:
    id: str
    save_path: str | None
    category: str
    torrent_tags: list[str]
    qbit_returns_torrent: bool  # whether qbit locates (returns) the torrent
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="returns qbit torrent and forwards args", save_path="/dl", category="anime",
         torrent_tags=["t1", "t2"], qbit_returns_torrent=True),
    Case(id="raises when qbit cannot locate torrent", save_path=None, category="anime",
         torrent_tags=[], qbit_returns_torrent=False,
         expected_exception=ExternalServiceException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_send_download_to_qbit(case: Case, make_torrent_download_component, make_qbit):
    component = make_torrent_download_component()
    qbit = make_qbit(hash="abc") if case.qbit_returns_torrent else None
    component._qbit_component.add_torrent = AsyncMock(return_value=qbit)

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await component.send_download_to_qbit(
                torrent_link="magnet:?xt=abc", magnet_hash="abc", save_path=case.save_path,
                category=case.category, torrent_tags=case.torrent_tags)
        return

    result = await component.send_download_to_qbit(
        torrent_link="magnet:?xt=abc", magnet_hash="abc", save_path=case.save_path,
        category=case.category, torrent_tags=case.torrent_tags)

    assert result is qbit
    component._qbit_component.add_torrent.assert_awaited_once_with(
        torrent_or_magnet_link="magnet:?xt=abc", magnet_hash="abc", save_path=case.save_path,
        category=case.category, tags=case.torrent_tags, resume_on_add=False)
