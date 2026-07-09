from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from config import config


def _torrent(*, magnet_hash="h1", preferred_title="Show Title", download=None, parent_torrent_id=None):
    tracked_anime = SimpleNamespace(preferred_title=preferred_title)
    episode = SimpleNamespace(tracked_anime=tracked_anime)
    return SimpleNamespace(magnet_hash=magnet_hash, tracked_anime_episode=episode, effective_download=download,
                           parent_torrent_id=parent_torrent_id)


@dataclass
class Case:
    id: str
    staging_directory: str | None = "/staging"
    organize_downloads: bool = True
    has_download: bool = False
    preferred_title: str = "My Show"
    expected_create: bool = True
    expected_directory: str | None = None    # normalized with forward slashes


CASES = [
    Case(id="organized directory appends the preferred title",
         expected_create=True, expected_directory="/staging/My Show"),
    Case(id="no staging directory passes None",
         staging_directory=None, expected_create=True, expected_directory=None),
    Case(id="existing download skips creation and returns it",
         has_download=True, expected_create=False),
    Case(id="organize disabled keeps the bare staging directory",
         organize_downloads=False, expected_create=True, expected_directory="/staging"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_select_torrents_for_downloading(case: Case, make_component):
    config.user_settings.staging_directory = case.staging_directory
    config.user_settings.organize_downloads = case.organize_downloads

    existing_download = SimpleNamespace(id=1) if case.has_download else None
    component = make_component()
    torrent = _torrent(magnet_hash="h1", preferred_title=case.preferred_title, download=existing_download)
    component.get_torrents_by_hashes = AsyncMock(return_value=[torrent])

    created_download = SimpleNamespace(id=2)
    create = component._torrent_download_component.create_downloads_for_torrent
    create.return_value = created_download

    result = await component.select_torrent_for_downloading(magnet_hash="h1")

    if not case.expected_create:
        create.assert_not_awaited()
        assert result is existing_download
        return

    create.assert_awaited_once()
    assert result is created_download
    assert create.await_args.kwargs["db_torrent_group"] == [torrent]
    directory = create.await_args.kwargs["download_directory_path"]
    if case.expected_directory is None:
        assert directory is None
    else:
        assert directory.replace("\\", "/") == case.expected_directory
