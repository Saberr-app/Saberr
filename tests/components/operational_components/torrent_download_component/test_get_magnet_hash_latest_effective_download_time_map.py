from dataclasses import dataclass, field
from datetime import datetime, UTC
from types import SimpleNamespace

import pytest

_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"
_METHOD = "get_latest_copied_to_destination_path_at_by_torrent_space"

_T1 = datetime(2024, 1, 1, tzinfo=UTC)
_T2 = datetime(2024, 1, 2, tzinfo=UTC)
_T3 = datetime(2024, 1, 3, tzinfo=UTC)


def torrent(magnet_hash, tae_id, *, part=0, ceiling=0):
    return SimpleNamespace(magnet_hash=magnet_hash, tracked_anime_episode_id=tae_id,
                           episode_part=part, episode_part_ceiling=ceiling)


@dataclass
class Case:
    id: str
    db_torrents: list
    rows: list  # (tae_id, episode_part, episode_part_ceiling, copied_at) from the repo
    expected_result: dict


CASES = [
    Case(id="no torrents yields empty map", db_torrents=[], rows=[], expected_result={}),
    # a space with no row is skipped entirely
    Case(id="space without a copied-at row is skipped",
         db_torrents=[torrent("a", 1)], rows=[], expected_result={}),
    Case(id="single torrent maps to its copied-at",
         db_torrents=[torrent("a", 1)], rows=[(1, 0, 0, _T1)],
         expected_result={"a": _T1}),
    # same hash across two spaces -> keep the latest copied-at
    Case(id="latest copied-at wins across spaces of the same hash",
         db_torrents=[torrent("a", 1), torrent("a", 2)],
         rows=[(1, 0, 0, _T1), (2, 0, 0, _T3)],
         expected_result={"a": _T3}),
    # distinct hashes are tracked independently
    Case(id="distinct hashes are mapped independently",
         db_torrents=[torrent("a", 1), torrent("b", 2)],
         rows=[(1, 0, 0, _T1), (2, 0, 0, _T2)],
         expected_result={"a": _T1, "b": _T2}),
    # the part/ceiling are part of the space key
    Case(id="part and ceiling distinguish spaces",
         db_torrents=[torrent("a", 1, part=1, ceiling=2), torrent("a", 1, part=2, ceiling=2)],
         rows=[(1, 1, 2, _T2), (1, 2, 2, _T3)],
         expected_result={"a": _T3}),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_magnet_hash_latest_effective_download_time_map(case: Case, make_torrent_download_component, mocker):
    mocker.patch(f"{_REPO}.{_METHOD}", return_value=case.rows)
    component = make_torrent_download_component()

    result = await component.get_magnet_hash_latest_effective_download_time_map(db_torrents=case.db_torrents)

    assert result == case.expected_result
