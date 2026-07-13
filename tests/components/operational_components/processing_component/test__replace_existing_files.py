import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest


@dataclass
class Case:
    id: str
    # tmp_path -> (existing_files, new_stem, target_video_path)
    setup: Callable[[Path], tuple[list[Path], str, Path]]
    check: Callable[[Path], None]  # asserts filesystem state given tmp_path
    expected_log_substring: str | None = None
    expected_no_logs: bool = False


def _restem_including_dirs(tmp_path: Path) -> tuple[list[Path], str, Path]:
    old_dir = tmp_path / "season"
    old_dir.mkdir()
    (old_dir / "Old.mkv").write_bytes(b"old-video")
    (old_dir / "Old.nfo").write_text("meta")
    (old_dir / "Old.en.srt").write_text("subs")
    (old_dir / "Old.trickplay").mkdir()
    (old_dir / "Old.trickplay" / "0.jpg").write_bytes(b"thumb")
    target_video_path = tmp_path / "other" / "New.mkv"  # elsewhere; nothing here should touch it
    return [old_dir / "Old.mkv"], "New", target_video_path


def _check_restem_including_dirs(tmp_path: Path):
    old_dir = tmp_path / "season"
    assert not (old_dir / "Old.mkv").exists()
    assert (old_dir / "New.nfo").read_text() == "meta"
    assert (old_dir / "New.en.srt").read_text() == "subs"
    assert (old_dir / "New.trickplay" / "0.jpg").read_bytes() == b"thumb"
    assert not (old_dir / "Old.nfo").exists()
    assert not (old_dir / "Old.trickplay").exists()


def _missing_existing_file(tmp_path: Path) -> tuple[list[Path], str, Path]:
    gone = tmp_path / "gone" / "Old.mkv"  # parent dir does not exist
    return [gone], "New", tmp_path / "New.mkv"


def _never_clobbers_target(tmp_path: Path) -> tuple[list[Path], str, Path]:
    # old stem == new stem in the same directory: the existing path *is* the new target.
    directory = tmp_path / "season"
    directory.mkdir()
    fresh = directory / "Show.mkv"
    fresh.write_bytes(b"fresh-copy")
    (directory / "Show.srt").write_text("subs")
    return [directory / "Show.mkv"], "Show", fresh


def _check_never_clobbers_target(tmp_path: Path):
    directory = tmp_path / "season"
    assert (directory / "Show.mkv").read_bytes() == b"fresh-copy"  # not deleted
    assert (directory / "Show.srt").read_text() == "subs"  # no-op rename, untouched


def _delete_failure(tmp_path: Path) -> tuple[list[Path], str, Path]:
    # make the "video" a (non-empty) directory so unlink() raises, but its sidecar still re-stems.
    directory = tmp_path / "season"
    directory.mkdir()
    (directory / "Old.mkv").mkdir()
    (directory / "Old.mkv" / "x").write_bytes(b"x")
    (directory / "Old.nfo").write_text("meta")
    return [directory / "Old.mkv"], "New", tmp_path / "New.mkv"


def _check_delete_failure(tmp_path: Path):
    assert (tmp_path / "season" / "New.nfo").read_text() == "meta"


def _rename_collision(tmp_path: Path) -> tuple[list[Path], str, Path]:
    directory = tmp_path / "season"
    directory.mkdir()
    (directory / "Old.mkv").write_bytes(b"old-video")
    (directory / "Old.srt").write_text("old-subs")
    (directory / "New.srt").write_text("stale-new-subs")  # collision target already present
    return [directory / "Old.mkv"], "New", tmp_path / "New.mkv"


def _check_rename_collision(tmp_path: Path):
    assert (tmp_path / "season" / "New.srt").read_text() == "old-subs"


CASES = [
    Case(id="deletes old video and re-stems sidecars including dirs",
         setup=_restem_including_dirs, check=_check_restem_including_dirs),
    Case(id="missing existing file is skipped without error",
         setup=_missing_existing_file, check=lambda tmp_path: None, expected_no_logs=True),
    Case(id="never clobbers the freshly copied target",
         setup=_never_clobbers_target, check=_check_never_clobbers_target),
    Case(id="delete failure is logged and processing continues",
         setup=_delete_failure, check=_check_delete_failure,
         expected_log_substring="Failed to delete"),
    Case(id="rename collision overwrites existing file",
         setup=_rename_collision, check=_check_rename_collision),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_replace_existing_files(case: Case, tmp_path, make_processing_component, caplog):
    component = make_processing_component()
    existing_files, new_stem, target_video_path = case.setup(tmp_path)

    with caplog.at_level(logging.WARNING):
        component._replace_existing_files(existing_files, new_stem, target_video_path)

    case.check(tmp_path)
    if case.expected_no_logs:
        assert not caplog.records
    if case.expected_log_substring is not None:
        assert any(case.expected_log_substring in record.message for record in caplog.records)
