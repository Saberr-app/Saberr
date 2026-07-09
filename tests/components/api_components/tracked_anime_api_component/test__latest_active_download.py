from dataclasses import dataclass
from datetime import datetime, UTC
from types import SimpleNamespace

import pytest

from components.api_components.tracked_anime_api_component import TrackedAnimeAPIComponent
from constants import TorrentDownloadStatus as Status

_T0 = datetime(2024, 1, 1, tzinfo=UTC)
_T1 = datetime(2024, 1, 2, tzinfo=UTC)
_T2 = datetime(2024, 1, 3, tzinfo=UTC)


def dl(id_, status, *, copied=None, created=_T0):
    return SimpleNamespace(id=id_, status=status,
                           copied_to_destination_path_at=copied, created_at=created)


def episode(*downloads):
    return SimpleNamespace(torrents=[SimpleNamespace(effective_download=d) for d in downloads])


@dataclass
class Case:
    id: str
    record: object
    expected_id: int | None


CASES = [
    Case(id="no torrents -> None", record=episode(), expected_id=None),
    Case(id="torrent with no effective download -> None", record=episode(None), expected_id=None),
    Case(id="only deleted/discarded downloads -> None",
         record=episode(dl(1, Status.DELETED), dl(2, Status.DISCARDED)), expected_id=None),
    Case(id="single active download is returned",
         record=episode(dl(7, Status.DOWNLOADING)), expected_id=7),
    # deleted one is filtered out, the active one wins
    Case(id="active download chosen over deleted sibling",
         record=episode(dl(1, Status.DELETED, copied=_T2), dl(2, Status.DOWNLOADING, copied=_T0)),
         expected_id=2),
    # latest wins by copied_to_destination_path_at
    Case(id="latest by copied timestamp wins",
         record=episode(dl(1, Status.PROCESSED, copied=_T1), dl(2, Status.PROCESSED, copied=_T2)),
         expected_id=2),
    # when copied is missing the sort falls back to created_at
    Case(id="falls back to created_at when copied is missing",
         record=episode(dl(1, Status.DOWNLOADING, copied=None, created=_T1),
                        dl(2, Status.DOWNLOADING, copied=None, created=_T2)),
         expected_id=2),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__latest_active_download(case: Case):
    result = TrackedAnimeAPIComponent._latest_active_download(case.record)
    assert (result.id if result else None) == case.expected_id
