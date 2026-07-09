from dataclasses import dataclass
from typing import Callable

import pytest

from components.api_components.system_api_component import SystemAPIComponent
from api.schemas.system_schemas import Task, TaskList


def _task(id_, currently_running=False):
    return Task(id=id_, name="Worker", category="cleanup", frequency=600, last_run=None,
                currently_running=currently_running, currently_running_since=None)


@dataclass
class Case:
    id: str
    old: Callable          # () -> TaskList | None
    new: Callable          # () -> TaskList
    expected_ids: list[str]


CASES = [
    Case(id="no previous state keeps everything", old=lambda: None,
         new=lambda: TaskList(ref=1, tasks=[_task("a")]), expected_ids=["a"]),
    Case(id="identical task is dropped", old=lambda: TaskList(ref=1, tasks=[_task("a")]),
         new=lambda: TaskList(ref=1, tasks=[_task("a")]), expected_ids=[]),
    Case(id="changed task is kept", old=lambda: TaskList(ref=1, tasks=[_task("a")]),
         new=lambda: TaskList(ref=1, tasks=[_task("a", currently_running=True)]), expected_ids=["a"]),
    Case(id="new task id is kept", old=lambda: TaskList(ref=1, tasks=[_task("a")]),
         new=lambda: TaskList(ref=1, tasks=[_task("a"), _task("b")]), expected_ids=["b"]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_nullify_unchanged(case: Case):
    new = case.new()
    SystemAPIComponent.nullify_unchanged(case.old(), new)
    assert [task.id for task in new.tasks] == case.expected_ids
