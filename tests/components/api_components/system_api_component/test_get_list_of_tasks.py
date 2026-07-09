from dataclasses import dataclass, field
from datetime import datetime, UTC

import pytest

from workers.worker_manager import WorkerDetails, WorkerLastRun

# SystemAPIComponent / app are imported inside the runner (see note in test_validate_path.py).

_LAST_RUN = WorkerLastRun(succeeded=False, last_run_time=datetime(2026, 1, 1, tzinfo=UTC),
                          last_run_duration=12, error="boom")


def _populated_workers() -> list[WorkerDetails]:
    return [
        WorkerDetails(id="a", name="Worker A", category="Cat", frequency=600,
                      last_run=_LAST_RUN, currently_running=True),
        WorkerDetails(id="b", name="Worker B", category="Other", frequency=None,
                      last_run=None, currently_running=False),
    ]


@dataclass
class Case:
    id: str
    workers: list[WorkerDetails] = field(default_factory=list)
    # when set, the runner checks the detailed per-field mapping of the first task
    check_detailed_mapping: bool = False
    expected_tuples: list[tuple] = field(default_factory=list)
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="maps worker details to tasks",
         workers=_populated_workers(),
         check_detailed_mapping=True,
         expected_tuples=[
             ("a", "Worker A", "Cat", 600, True),
             ("b", "Worker B", "Other", None, False),
         ]),
    Case(id="empty worker list", workers=[], expected_tuples=[]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_list_of_tasks(case: Case, monkeypatch):
    from app_state import worker_manager
    from components.api_components.system_api_component import SystemAPIComponent

    monkeypatch.setattr(worker_manager, "get_worker_list", lambda: case.workers)

    result = await SystemAPIComponent().get_list_of_tasks()

    if not case.workers:
        assert result.tasks == case.expected_tuples
        return

    assert [(t.id, t.name, t.category, t.frequency, t.currently_running)
            for t in result.tasks] == case.expected_tuples

    if case.check_detailed_mapping:
        a = result.tasks[0]
        assert a.last_run.run_succeeded is False
        assert a.last_run.run_time == datetime(2026, 1, 1, tzinfo=UTC)
        assert a.last_run.run_duration == 12
        assert a.last_run.run_error == "boom"
        assert result.tasks[1].last_run is None
