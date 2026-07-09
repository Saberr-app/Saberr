from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest

from components.operational_components.processing_component import ProcessingComponent


@dataclass
class Case:
    id: str
    setup: Callable[[Path], tuple[Path, Path]]  # tmp_path -> (source, target)
    expected_bytes: bytes


def _content_and_missing_parents(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source.mkv"
    source.write_bytes(b"video-bytes")
    target = tmp_path / "dest" / "season" / "New.mkv"
    return source, target


def _overwrite_existing(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source.mkv"
    source.write_bytes(b"new-content")
    target = tmp_path / "New.mkv"
    target.write_bytes(b"old-content")
    return source, target


CASES = [
    Case(id="copies content and creates missing parents",
         setup=_content_and_missing_parents, expected_bytes=b"video-bytes"),
    Case(id="overwrites existing target",
         setup=_overwrite_existing, expected_bytes=b"new-content"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_copy_file(case: Case, tmp_path):
    source, target = case.setup(tmp_path)

    ProcessingComponent._copy_file(source, target)

    assert target.read_bytes() == case.expected_bytes
