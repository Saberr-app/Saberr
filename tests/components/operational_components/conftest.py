import logging
from itertools import count
from unittest.mock import AsyncMock, MagicMock

import pytest

from constants import (Encoding, Resolution, TorrentDownloadStatus, TrackedAnimeStatus, TVDBSeasonType,
                       VideoSource)
from dto.orm_models import Torrent, TorrentDownload, TrackedAnime, TrackedAnimeEpisode

# In-memory ORM builders. No DB: ids are assigned from a counter and relationships are wired directly,
# so graphs like `download.torrent.tracked_anime_episode.tracked_anime` are reachable without a session.
_ids = count(1)


@pytest.fixture
def make_tracked_anime():
    def _make(*, anilist_id=1, tvdb_structure_enabled=False, tvdb_season_type=TVDBSeasonType.OFFICIAL,
              title="Show", show_parent_directory="/library", show_folder_name="Show", **kw):
        tracked_anime = TrackedAnime(romaji_title=title, anilist_id=anilist_id, status=TrackedAnimeStatus.ACTIVE,
                                     show_parent_directory=show_parent_directory,
                                     show_folder_name=show_folder_name,
                                     tvdb_structure_enabled=tvdb_structure_enabled,
                                     tvdb_season_type=tvdb_season_type, **kw)
        tracked_anime.id = next(_ids)
        return tracked_anime
    return _make


@pytest.fixture
def make_tracked_anime_episode(make_tracked_anime):
    def _make(*, tracked_anime_id=None, tracked_anime=None, episode_number=1, tvdb_episode_ids=None,
              tvdb_episode_numbers=None, **kw):
        if tracked_anime is None and tracked_anime_id is None:
            tracked_anime = make_tracked_anime()
        episode = TrackedAnimeEpisode(
            tracked_anime_id=tracked_anime_id if tracked_anime_id is not None else tracked_anime.id,
            episode_number=episode_number,
            tvdb_episode_ids=tvdb_episode_ids if tvdb_episode_ids is not None else [],
            tvdb_episode_numbers=tvdb_episode_numbers if tvdb_episode_numbers is not None else [], **kw)
        episode.id = next(_ids)
        if tracked_anime is not None:
            episode.tracked_anime = tracked_anime
        return episode
    return _make


@pytest.fixture
def make_torrent():
    def _make(*, tracked_anime_episode_id=None, tracked_anime_episode=None, magnet_hash=None,
              episode_number=1, episode_part=0, episode_part_ceiling=0, release_group="GroupA",
              language_code="eng", encoding=Encoding.HEVC, resolution=Resolution.P1080,
              source=VideoSource.OTHER, **kw):
        n = next(_ids)
        magnet_hash = magnet_hash or f"hash-{n}"
        torrent = Torrent(
            tracked_anime_episode_id=(tracked_anime_episode_id if tracked_anime_episode_id is not None
                                      else (tracked_anime_episode.id if tracked_anime_episode else None)),
            magnet_hash=magnet_hash, rss_xml="<item/>", torrent_link=f"magnet:?xt={magnet_hash}",
            torrent_title=f"[{release_group}] Show - {episode_number:02d}", release_group=release_group,
            title="Show", episode_number=episode_number, episode_part=episode_part,
            episode_part_ceiling=episode_part_ceiling, language_code=language_code, encoding=encoding,
            resolution=resolution, source=source, **kw)
        torrent.id = n
        if tracked_anime_episode is not None:
            torrent.tracked_anime_episode = tracked_anime_episode
        return torrent
    return _make


@pytest.fixture
def make_torrent_download():
    def _make(*, torrent_id=None, torrent=None, status=TorrentDownloadStatus.PENDING,
              download_directory_path="/staging", destination_path=None, status_retry_count=0,
              status_details=None, **kw):
        download = TorrentDownload(
            torrent_id=torrent_id if torrent_id is not None else (torrent.id if torrent else None),
            status=status, download_directory_path=download_directory_path,
            destination_path=destination_path, status_retry_count=status_retry_count,
            status_details=status_details, **kw)
        download.id = next(_ids)
        if torrent is not None:
            download.torrent = torrent
        return download
    return _make


@pytest.fixture
def make_download_chain(make_tracked_anime, make_tracked_anime_episode, make_torrent,
                        make_torrent_download):
    """Build anime → episode → torrent → download in one call, with relationships wired in memory so
    `.torrent.tracked_anime_episode.tracked_anime` is reachable."""
    _anilist = count(1001)

    def _make(*, anilist_id=None, tvdb_structure_enabled=False, episode_number=1, episode_part=0,
              episode_part_ceiling=0, tvdb_episode_ids=None,
              status=TorrentDownloadStatus.PENDING, **download_kw):
        anime = make_tracked_anime(anilist_id=anilist_id if anilist_id is not None else next(_anilist),
                                   tvdb_structure_enabled=tvdb_structure_enabled)
        episode = make_tracked_anime_episode(tracked_anime=anime, episode_number=episode_number,
                                             tvdb_episode_ids=tvdb_episode_ids)
        torrent = make_torrent(tracked_anime_episode=episode, episode_number=episode_number,
                               episode_part=episode_part, episode_part_ceiling=episode_part_ceiling)
        return make_torrent_download(torrent=torrent, status=status, **download_kw)
    return _make


@pytest.fixture
def make_qbit():
    from dto.qbit import QBitTorrent

    def _make(*, hash="h", state="uploading", progress=1.0, save_path="/dl"):
        return QBitTorrent(amount_left=0, eta=None, hash=hash, name="n", progress=progress,
                           save_path=save_path, content_path=f"{save_path}/n", state=state, size=1,
                           original_save_path=save_path, original_content_path=f"{save_path}/n")
    return _make


@pytest.fixture
def make_processing_component():
    """A ProcessingComponent without its heavy __init__; sub-components are mocks."""
    from components.operational_components.processing_component import ProcessingComponent

    def _make():
        component = ProcessingComponent.__new__(ProcessingComponent)
        component.logger = logging.getLogger("test.processing_component")
        component._tracked_anime_episode_component = MagicMock()
        component._tracked_anime_episode_component.get_or_create_tracked_anime_episode = AsyncMock()
        component._audit_log_component = AsyncMock()
        return component
    return _make


@pytest.fixture
def make_torrent_download_component():
    """A TorrentDownloadComponent without its heavy __init__; sub-components are mocks."""
    from components.operational_components.torrent_download_component import TorrentDownloadComponent

    def _make():
        component = TorrentDownloadComponent.__new__(TorrentDownloadComponent)
        component.logger = logging.getLogger("test.torrent_download_component")
        for name in ("_qbit_component", "_processing_component", "_anilist_component",
                     "_tracked_anime_component", "_tracked_anime_episode_component"):
            setattr(component, name, MagicMock())
        component._audit_log_component = AsyncMock()
        return component
    return _make
