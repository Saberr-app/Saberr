from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

import pytest

from app_state import worker_manager
from components.api_components.torrent_api_component import TorrentAPIComponent
from components.service_components.rss_component import RSSComponent

_RSS_LOCKED = "components.service_components.rss_component.RSSComponent.rss_locked"

_LAST_RUN_TIME = datetime(2024, 5, 6, 7, 8, 9)
_NEXT_RUN_TIME = datetime(2024, 5, 6, 8, 8, 9)


def _component() -> TorrentAPIComponent:
    component = TorrentAPIComponent.__new__(TorrentAPIComponent)
    component._rss_component = RSSComponent.__new__(RSSComponent)
    return component


@dataclass
class Case:
    id: str
    worker_details: object | None
    currently_pulling: bool
    expected_last_pull: datetime | None


CASES = [
    Case(id="worker with a last run reports its time",
         worker_details=SimpleNamespace(last_run=SimpleNamespace(last_run_time=_LAST_RUN_TIME)),
         currently_pulling=True, expected_last_pull=_LAST_RUN_TIME),
    Case(id="no worker details -> no last pull",
         worker_details=None, currently_pulling=False, expected_last_pull=None),
    Case(id="worker without a last run -> no last pull",
         worker_details=SimpleNamespace(last_run=None), currently_pulling=False, expected_last_pull=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_torrents_pull_status(case: Case, mocker):
    mocker.patch.object(worker_manager, "get_worker_details", return_value=case.worker_details)
    mocker.patch.object(worker_manager, "get_worker_next_run", return_value=_NEXT_RUN_TIME)
    mocker.patch(_RSS_LOCKED, return_value=case.currently_pulling)

    status = await _component().get_torrents_pull_status(ref=42)

    assert status.ref == 42
    assert status.currently_pulling == case.currently_pulling
    assert status.last_pull == case.expected_last_pull
    assert status.next_pull == _NEXT_RUN_TIME
