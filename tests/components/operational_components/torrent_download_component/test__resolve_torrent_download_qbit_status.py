from dataclasses import dataclass

import pytest

from components.operational_components.torrent_download_component import TorrentDownloadComponent
from constants import TorrentDownloadStatus as Status
from dto.qbit import QBitTorrent

resolve = TorrentDownloadComponent._resolve_torrent_download_qbit_status


def _qbit(state, progress):
    return QBitTorrent(amount_left=0, eta=None, hash="h", name="n", progress=progress,
                       save_path="/s", content_path="/s/n", state=state, size=1,
                       original_save_path="/s", original_content_path="/s/n")


@dataclass
class Case:
    id: str
    current_status: Status
    qbit_state: str | None  # None => no qbit download present
    qbit_progress: float
    expected: Status


CASES = [
    Case(id="missing-init-stays-init", current_status=Status.FAILED_DOWNLOAD_INIT,
         qbit_state=None, qbit_progress=0, expected=Status.FAILED_DOWNLOAD_INIT),
    Case(id="missing-otherwise-deleted", current_status=Status.DOWNLOADING,
         qbit_state=None, qbit_progress=0, expected=Status.DELETED),
    Case(id="error-state", current_status=Status.DOWNLOADING,
         qbit_state="error", qbit_progress=1, expected=Status.FAILED_DOWNLOAD),
    Case(id="missing-files-state", current_status=Status.DOWNLOADING,
         qbit_state="missingFiles", qbit_progress=0.5, expected=Status.FAILED_DOWNLOAD),
    Case(id="unfinished-state", current_status=Status.DOWNLOADING,
         qbit_state="downloading", qbit_progress=0.5, expected=Status.DOWNLOADING),
    Case(id="finished-state-but-incomplete-progress", current_status=Status.DOWNLOADING,
         qbit_state="uploading", qbit_progress=0.5, expected=Status.DOWNLOADING),
    Case(id="unfinished-takes-precedence-over-complete-progress", current_status=Status.DOWNLOADING,
         qbit_state="stalledDL", qbit_progress=1, expected=Status.DOWNLOADING),
    Case(id="complete", current_status=Status.DOWNLOADING,
         qbit_state="uploading", qbit_progress=1, expected=Status.DOWNLOADED),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__resolve_torrent_download_qbit_status(case: Case):
    qbit_download = None if case.qbit_state is None else _qbit(case.qbit_state, case.qbit_progress)
    assert resolve(qbit_download=qbit_download, current_status=case.current_status) == case.expected
