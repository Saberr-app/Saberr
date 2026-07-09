import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pytest


def _make_video(tmp_path, name="video.mkv"):
    video = tmp_path / name
    video.write_bytes(b"v")
    return video


@dataclass
class Case:
    id: str
    # tmp_path -> (related_paths, new_stem); creates sidecar files as needed
    setup: Callable[[Path], tuple[list[Path], str]]
    expected_files: dict[str, str] = field(default_factory=dict)  # relative-to-out name -> text content
    expected_absent: list[str] = field(default_factory=list)
    expected_logged: bool = False


def _single_suffix(tmp_path: Path) -> tuple[list[Path], str]:
    sub = tmp_path / "video.srt"
    sub.write_text("sub")
    return [sub], "New Name - 01"


def _multi_dot(tmp_path: Path) -> tuple[list[Path], str]:
    sub = tmp_path / "video.en.srt"
    sub.write_text("english")
    return [sub], "New"


def _not_prefixed(tmp_path: Path) -> tuple[list[Path], str]:
    sub = tmp_path / "unrelated.ass"  # does not start with the video stem
    sub.write_text("styled")
    return [sub], "New"


def _failing_and_present(tmp_path: Path) -> tuple[list[Path], str]:
    missing = tmp_path / "video.missing.srt"  # never created -> copy raises
    present = tmp_path / "video.ass"
    present.write_text("ok")
    return [missing, present], "New"


CASES = [
    Case(id="single-suffix sidecar is re-stemmed",
         setup=_single_suffix,
         expected_files={"New Name - 01.srt": "sub"}),
    Case(id="multi-dot sidecar preserves language tag",
         setup=_multi_dot,
         expected_files={"New.en.srt": "english"}),
    Case(id="sidecar not prefixed by stem falls back to suffix",
         setup=_not_prefixed,
         expected_files={"New.ass": "styled"}),
    Case(id="failing file is logged and others still copied",
         setup=_failing_and_present,
         expected_files={"New.ass": "ok"},
         expected_absent=["New.missing.srt"],
         expected_logged=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_copy_related_files(case: Case, tmp_path, make_processing_component, caplog):
    component = make_processing_component()
    video = _make_video(tmp_path)
    related, new_stem = case.setup(tmp_path)
    target_dir = tmp_path / "out"

    with caplog.at_level(logging.ERROR):
        component._copy_related_files(related, video, target_dir, new_stem)

    for name, text in case.expected_files.items():
        assert (target_dir / name).read_text() == text
    for name in case.expected_absent:
        assert not (target_dir / name).exists()
    if case.expected_logged:
        assert any("Failed to copy related file" in record.message for record in caplog.records)
