from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

# SystemAPIComponent / app are imported inside the runner (see note in test_validate_path.py).


@dataclass
class Case:
    id: str
    task_id: str
    expected_worker_id: str
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="delegates to worker manager", task_id="some-id", expected_worker_id="some-id"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_trigger_task(case: Case, monkeypatch):
    from app_state import worker_manager
    from components.api_components.system_api_component import SystemAPIComponent

    trigger = AsyncMock()
    monkeypatch.setattr(worker_manager, "trigger_worker", trigger)

    await SystemAPIComponent().trigger_task(task_id=case.task_id)

    trigger.assert_awaited_once_with(worker_id=case.expected_worker_id)
