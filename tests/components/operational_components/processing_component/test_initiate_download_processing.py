from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Callable
from unittest.mock import AsyncMock, MagicMock

import pytest

import components.operational_components.processing_component as pc_module
from common.exceptions import PreprocessingFailedException
from constants import TorrentDownloadStatus
from dto.qbit import QBitTorrent

_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"


def _qbit():
    return QBitTorrent(amount_left=0, eta=None, hash="h", name="release.name", progress=1.0,
                       save_path="/dl", content_path="/dl/release", state="uploading", size=1,
                       original_save_path="/dl", original_content_path="/dl/release")


@pytest.fixture
def pc_env(monkeypatch, make_processing_component):
    component = make_processing_component()
    component._finalize_download_processing = MagicMock()

    env = SimpleNamespace(
        component=component,
        video=Path("/dl/release/video.mkv"),
        related=[Path("/dl/release/video.srt")],
        episode_stub=SimpleNamespace(tvdb_series_id=55, tvdb_episode_ids=[100]),
        tvdb_episodes=[SimpleNamespace(id=100, season_number=2)],
    )
    component._tracked_anime_episode_component.get_or_create_tracked_anime_episode = \
        AsyncMock(return_value=env.episode_stub)

    monkeypatch.setattr(pc_module.QBitComponent, "find_download_files",
                        lambda qbit_torrent: (env.video, env.related))

    anilist = MagicMock(get_anime=AsyncMock(return_value=MagicMock()))
    monkeypatch.setattr(pc_module, "AnilistComponent", MagicMock(return_value=anilist))

    tvdb = MagicMock(get_series=AsyncMock(return_value=MagicMock()))
    tvdb.get_series_episodes = AsyncMock(return_value=SimpleNamespace(episodes=env.tvdb_episodes))
    env.tvdb_class = MagicMock(return_value=tvdb)
    monkeypatch.setattr(pc_module, "TVDBComponent", env.tvdb_class)

    monkeypatch.setattr(pc_module, "format_season_directory_name", lambda **kw: "Season 02")
    monkeypatch.setattr(pc_module, "format_file_name", lambda **kw: "Show - 01")
    return env


@dataclass
class Case:
    id: str
    tvdb_structure_enabled: bool = False
    mutate_env: Callable | None = None
    existing_destinations: list[str] = field(default_factory=list)
    expected_exception: type[Exception] | None = None
    check: Callable | None = None


def _check_tvdb_disabled(env, download):
    assert env._result == Path("/library").resolve() / "Show" / "Show - 01.mkv"
    assert not env.tvdb_class.called
    assert env._task is env.component._finalize_download_processing.return_value
    kwargs = env.component._finalize_download_processing.call_args.kwargs
    assert kwargs["target_directory"] == Path("/library").resolve() / "Show"
    assert kwargs["target_file_name"] == "Show - 01"
    assert kwargs["source_video_file_path"] == env.video
    assert kwargs["source_related_file_paths"] == env.related
    assert kwargs["torrent_download_ids"] == [download.id]
    assert kwargs["existing_files"] == []


def _check_tvdb_enabled(env, download):
    expected_dir = Path("/library").resolve() / "Show" / "Season 02"
    assert env._result == expected_dir / "Show - 01.mkv"
    assert env.component._finalize_download_processing.call_args.kwargs["target_directory"] == expected_dir


def _no_video(env):
    env.video, env.related = None, []


def _incomplete_tvdb(env):
    env.episode_stub.tvdb_episode_ids = [100, 200]  # 200 won't be among the returned episodes


def _check_existing_passed(env, download):
    existing = env.component._finalize_download_processing.call_args.kwargs["existing_files"]
    assert Path("/library/Show/Old.mkv").resolve() in existing


CASES = [
    Case(id="tvdb disabled returns path and finalize task", check=_check_tvdb_disabled),
    Case(id="tvdb enabled inserts season directory", tvdb_structure_enabled=True, check=_check_tvdb_enabled),
    Case(id="no video file raises and skips finalize", mutate_env=_no_video,
         expected_exception=PreprocessingFailedException),
    Case(id="tvdb incomplete data raises", tvdb_structure_enabled=True, mutate_env=_incomplete_tvdb,
         expected_exception=PreprocessingFailedException),
    Case(id="existing processed paths passed to finalize",
         existing_destinations=["/library/Show/Old.mkv"], check=_check_existing_passed),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_initiate_download_processing(case: Case, pc_env, make_download_chain,
                                            make_torrent_download, mocker):
    if case.mutate_env is not None:
        case.mutate_env(pc_env)
    download = make_download_chain(tvdb_structure_enabled=case.tvdb_structure_enabled)

    existing = [make_torrent_download(torrent_id=99, status=TorrentDownloadStatus.PROCESSED,
                                      destination_path=dest)
                for dest in case.existing_destinations]
    mocker.patch(f"{_REPO}.get_by_episode_id_and_part", return_value=existing)

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await pc_env.component.initiate_download_processing(torrent_downloads=[download],
                                                                qbit_torrent=_qbit())
        assert not pc_env.component._finalize_download_processing.called
        return

    pc_env._result, pc_env._source, pc_env._task = await pc_env.component.initiate_download_processing(
        torrent_downloads=[download], qbit_torrent=_qbit())
    case.check(pc_env, download)
