from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest

from common.exceptions import ValidationException
from api.schemas.system_schemas import ValidatePathRequest

# NB: SystemAPIComponent is imported inside the runner, not at module top — it does
# `from app import worker_manager`, which executes app.py's module-level singletons that read
# config.user_settings (only populated once the session-autouse app_startup fixture has run).


@dataclass
class Case:
    id: str
    # path is built from tmp_path so cases stay independent of the filesystem
    path: Callable[[Path], str]
    validate_writable: bool
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="existing writable directory passes",
         path=lambda tmp: str(tmp), validate_writable=True),
    Case(id="relative path raises validation",
         path=lambda tmp: "relative/dir", validate_writable=False,
         expected_exception=ValidationException),
    Case(id="nonexistent directory raises validation",
         path=lambda tmp: str(tmp / "missing"), validate_writable=True,
         expected_exception=ValidationException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_validate_path(case: Case, tmp_path):
    from components.api_components.system_api_component import SystemAPIComponent

    body = ValidatePathRequest(path=case.path(tmp_path), validate_writable=case.validate_writable)

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await SystemAPIComponent().validate_path(body=body)
        return

    # no exception => valid
    await SystemAPIComponent().validate_path(body=body)
