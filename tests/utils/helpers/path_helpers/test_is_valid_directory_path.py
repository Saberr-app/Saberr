from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from utils.helpers.path_helpers import is_valid_directory_path


@dataclass
class Case:
    id: str
    expected_result: bool
    path: str | None = None
    # When set, the path is built from the tmp_path fixture at runtime.
    path_factory: Callable[[Path], str] | None = None
    validate_writability: bool = True


# Format gate: relative paths are rejected regardless of the writability flag. The original
# test was a cross-product of these paths with validate_writability in (True, False).
_RELATIVE_PATHS = [
    ("relative/dir", "relative-dir"),
    ("./dir", "dot-dir"),
    ("../dir", "dotdot-dir"),
    ("dir", "bare-dir"),
    ("", "empty"),
    ("C:relative", "drive-relative"),  # drive-relative (no slash after colon) counts as relative
]

CASES = [
    *[
        Case(id=f"relative rejected: {name} (validate={validate})", path=path,
             validate_writability=validate, expected_result=False)
        for path, name in _RELATIVE_PATHS
        for validate in (True, False)
    ],
    # validate_writability=False skips the filesystem probe; any root-based path is accepted.
    Case(id="root posix passes format", path="/abs/posix/dir",
         validate_writability=False, expected_result=True),
    Case(id="root windows backslash passes format", path="C:\\abs\\windows\\dir",
         validate_writability=False, expected_result=True),
    Case(id="root windows forwardslash passes format", path="C:/abs/windows/dir",
         validate_writability=False, expected_result=True),
    Case(id="null byte rejected (probing)", path="/tmp\x00/x",
         validate_writability=True, expected_result=False),
    Case(id="null byte rejected (not probing)", path="/tmp\x00/x",
         validate_writability=False, expected_result=False),
    # Writability probe.
    Case(id="existing writable directory passes", path_factory=lambda tp: str(tp),
         validate_writability=True, expected_result=True),
    Case(id="nonexistent directory fails probe",
         path_factory=lambda tp: str(tp / "does_not_exist"),
         validate_writability=True, expected_result=False),
    # "." is writable, but a relative path never reaches the probe.
    Case(id="relative writable dir rejected before probe", path=".",
         validate_writability=True, expected_result=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_is_valid_directory_path(case: Case, tmp_path):
    path = case.path_factory(tmp_path) if case.path_factory is not None else case.path
    assert is_valid_directory_path(path, validate_writability=case.validate_writability) is case.expected_result
