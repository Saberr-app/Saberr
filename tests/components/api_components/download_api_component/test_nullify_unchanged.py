from dataclasses import dataclass

import pytest

from api.schemas.download_schemas import DownloadUpdatesStreamResponse
from components.api_components.download_api_component import DownloadAPIComponent
from constants import TorrentDownloadStatus

Item = DownloadUpdatesStreamResponse.DownloadStreamItem


def item(id_, **kwargs):
    return Item(id=id_, **kwargs)


def response(items):
    return DownloadUpdatesStreamResponse(ref=1, changed=list(items))


@dataclass
class Case:
    id: str
    old: DownloadUpdatesStreamResponse | None
    new: DownloadUpdatesStreamResponse
    expected_changed: list


CASES = [
    # no previous frame -> nothing is stripped
    Case(id="old is None leaves new untouched",
         old=None,
         new=response([item(1, status=TorrentDownloadStatus.DOWNLOADING)]),
         expected_changed=[item(1, status=TorrentDownloadStatus.DOWNLOADING)]),
    # identical to the previous frame -> dropped
    Case(id="unchanged item is stripped",
         old=response([item(1, status=TorrentDownloadStatus.DOWNLOADING)]),
         new=response([item(1, status=TorrentDownloadStatus.DOWNLOADING)]),
         expected_changed=[]),
    # same id but a differing field -> kept
    Case(id="changed item is kept",
         old=response([item(1, status=TorrentDownloadStatus.DOWNLOADING, qbit_progress=0.5)]),
         new=response([item(1, status=TorrentDownloadStatus.DOWNLOADING, qbit_progress=0.9)]),
         expected_changed=[item(1, status=TorrentDownloadStatus.DOWNLOADING, qbit_progress=0.9)]),
    # id absent from the previous frame -> kept
    Case(id="new item is kept",
         old=response([item(1, status=TorrentDownloadStatus.DOWNLOADING)]),
         new=response([item(2, status=TorrentDownloadStatus.PROCESSING)]),
         expected_changed=[item(2, status=TorrentDownloadStatus.PROCESSING)]),
    # mix: one unchanged (dropped), one changed (kept), one brand new (kept)
    Case(id="mixed frame keeps only changed and new",
         old=response([item(1, status=TorrentDownloadStatus.DOWNLOADING),
                       item(2, qbit_progress=0.5)]),
         new=response([item(1, status=TorrentDownloadStatus.DOWNLOADING),
                       item(2, qbit_progress=0.8),
                       item(3, status=TorrentDownloadStatus.PENDING)]),
         expected_changed=[item(2, qbit_progress=0.8),
                           item(3, status=TorrentDownloadStatus.PENDING)]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_nullify_unchanged(case: Case):
    result = DownloadAPIComponent.nullify_unchanged(case.old, case.new)
    assert result is None  # mutates `new` in place
    assert case.new.changed == case.expected_changed
