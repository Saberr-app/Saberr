import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from unittest.mock import MagicMock

import pytest

from constants import AuditLogCode, TorrentDownloadStatus

_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"


@dataclass
class Case:
    id: str
    # tmp_path -> kwargs for _finalize_download_processing (minus torrent_download_ids)
    finalize_kwargs: Callable[[Path], dict]
    check: Callable  # (tmp_path, component, update_mock) -> None
    expected_logged: bool = False


def _success_kwargs(tmp_path: Path) -> dict:
    source_video = tmp_path / "src.mkv"
    source_video.write_bytes(b"v")
    source_sub = tmp_path / "src.en.srt"
    source_sub.write_text("subs")
    return dict(target_directory=tmp_path / "out", target_file_name="New",
                source_video_file_path=source_video, source_related_file_paths=[source_sub],
                existing_files=[])


def _check_success(tmp_path, component, update_mock):
    target_dir = tmp_path / "out"
    assert (target_dir / "New.mkv").read_bytes() == b"v"
    assert (target_dir / "New.en.srt").read_text() == "subs"
    assert update_mock.await_args.kwargs["status"] == TorrentDownloadStatus.PROCESSED
    assert component._audit_log_component.log_torrent_processing_action.await_args.kwargs["code"] == \
        AuditLogCode.TORRENT_PROCESSING_FINISHED


def _replace_kwargs(tmp_path: Path) -> dict:
    source_video = tmp_path / "src.mkv"
    source_video.write_bytes(b"v")
    target_dir = tmp_path / "out"
    target_dir.mkdir()
    (target_dir / "Old.mkv").write_bytes(b"old")
    (target_dir / "Old.nfo").write_text("meta")
    return dict(target_directory=target_dir, target_file_name="New",
                source_video_file_path=source_video, source_related_file_paths=[],
                existing_files=[target_dir / "Old.mkv"])


def _check_replace(tmp_path, component, update_mock):
    target_dir = tmp_path / "out"
    assert not (target_dir / "Old.mkv").exists()
    assert (target_dir / "New.nfo").read_text() == "meta"
    assert (target_dir / "New.mkv").read_bytes() == b"v"


def _non_critical_kwargs(tmp_path: Path) -> dict:
    source_video = tmp_path / "src.mkv"
    source_video.write_bytes(b"v")
    return dict(target_directory=tmp_path / "out", target_file_name="New",
                source_video_file_path=source_video,
                source_related_file_paths=[tmp_path / "src.missing.srt"],  # absent -> related copy fails
                existing_files=[])


def _check_non_critical(tmp_path, component, update_mock):
    assert (tmp_path / "out" / "New.mkv").read_bytes() == b"v"
    assert update_mock.await_args.kwargs["status"] == TorrentDownloadStatus.PROCESSED


def _critical_kwargs(tmp_path: Path) -> dict:
    return dict(target_directory=tmp_path / "out", target_file_name="New",
                source_video_file_path=tmp_path / "does-not-exist.mkv",  # copy raises -> critical failure
                source_related_file_paths=[], existing_files=[])


def _check_critical(tmp_path, component, update_mock):
    assert update_mock.await_args.kwargs["status"] == TorrentDownloadStatus.FAILED_PROCESSING
    assert component._audit_log_component.log_torrent_processing_action.await_args.kwargs["code"] == \
        AuditLogCode.TORRENT_PROCESSING_FAILED


CASES = [
    Case(id="success copies files and marks processed",
         finalize_kwargs=_success_kwargs, check=_check_success),
    Case(id="replaces existing via public method",
         finalize_kwargs=_replace_kwargs, check=_check_replace),
    Case(id="non-critical failure still marks processed",
         finalize_kwargs=_non_critical_kwargs, check=_check_non_critical, expected_logged=True),
    Case(id="critical failure marks downloads failed processing",
         finalize_kwargs=_critical_kwargs, check=_check_critical),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_finalize_download_processing(case: Case, tmp_path, make_processing_component,
                                            make_download_chain, caplog, mocker):
    component = make_processing_component()
    kwargs = case.finalize_kwargs(tmp_path)
    download = make_download_chain(status=TorrentDownloadStatus.PROCESSING)
    mocker.patch(f"{_REPO}.get_downloads", return_value=[download])
    update_mock = mocker.patch(f"{_REPO}.update_downloads")

    with caplog.at_level(logging.DEBUG):
        # magnet_hash/anilist_anime/tvdb_episodes only feed the discord step, which is off by default
        await component._finalize_download_processing(
            torrent_download_ids=[download.id], magnet_hash="h",
            anilist_anime=MagicMock(), tvdb_episodes=[], **kwargs)

    case.check(tmp_path, component, update_mock)
    if case.expected_logged:
        assert any("Failed to copy related file" in r.message for r in caplog.records)
