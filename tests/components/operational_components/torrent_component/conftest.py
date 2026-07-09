import logging
from itertools import count
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from config import config
from constants import Encoding, Resolution, VideoSource

_ids = count(1)


@pytest.fixture
def make_component():
    """A TorrentComponent without its heavy __init__.

    Most methods reach the DB through `TorrentRepo` (patched per test at class level); only
    `select_torrents_for_downloading` delegates to `_torrent_download_component`, which is a mock here.
    """
    from components.operational_components.torrent_component import TorrentComponent

    def _make():
        component = TorrentComponent.__new__(TorrentComponent)
        component.logger = logging.getLogger("test.torrent_component")
        component._torrent_download_component = MagicMock()
        component._torrent_download_component.create_downloads_for_torrent = AsyncMock()
        component._tracked_anime_component = MagicMock()
        component._anilist_component = MagicMock()
        component._tracked_anime_episode_component = MagicMock()
        component._audit_log_component = AsyncMock()
        return component
    return _make


@pytest.fixture
def make_title_parts():
    """Stand-in for ReleaseTitleParts as read by `_populate_raw_torrent` (attribute access only)."""
    def _make(*, episode_number=5, title="Show", search_title=None, release_group=None, language_code="eng",
              encoding=Encoding.HEVC, resolution=Resolution.P1080, source=VideoSource.CRUNCHYROLL,
              version_number=1, repack_indicator=False):
        # default to a real configured release group so the `config.release_groups` lookup resolves
        release_group = release_group if release_group is not None\
            else next(config.release_groups_map.keys().__iter__())
        return SimpleNamespace(episode_number=episode_number, title=title,
                               search_title=search_title if search_title is not None else title,
                               release_group=release_group, language_code=language_code, encoding=encoding,
                               resolution=resolution, source=source, version_number=version_number,
                               repack_indicator=repack_indicator)
    return _make


@pytest.fixture
def make_raw_torrent(make_title_parts):
    """A real RawTorrent (so notes/flags behave) wrapping a lightweight nyaa item + title parts."""
    from dto.nyaa_item import RawTorrent

    def _make(*, magnet_hash="hash-1", title_parts=None):
        nyaa_item = SimpleNamespace(magnet_hash=magnet_hash, source_xml="<item/>",
                                    title="[Group] Show - 05", link=f"magnet:?xt={magnet_hash}")
        return RawTorrent(nyaa_item=nyaa_item, title_parts=title_parts or make_title_parts(),
                          release_group_settings=None, anilist_anime_min=None, anilist_episode_number=None)
    return _make


@pytest.fixture
def make_profile():
    """Stand-in for a TrackedAnimeProfile as read by the candidacy logic (attribute access only)."""
    def _make(*, preferred_release_groups=None, preferred_encodings=None, preferred_resolutions=None,
              preferred_sources=None, preferred_language_codes=None, sources_restricted=False,
              language_codes_restricted=False, accept_release_upgrades=True, priorities_sorted=None):
        return SimpleNamespace(
            preferred_release_groups=preferred_release_groups or [],
            preferred_encodings=preferred_encodings or [],
            preferred_resolutions=preferred_resolutions or [],
            preferred_sources=preferred_sources or [],
            preferred_language_codes=preferred_language_codes or [],
            sources_restricted=sources_restricted,
            language_codes_restricted=language_codes_restricted,
            accept_release_upgrades=accept_release_upgrades,
            priorities_sorted=priorities_sorted or [],
        )
    return _make


@pytest.fixture
def make_candidate():
    """Build an in-memory torrent for the candidacy algorithm.

    The algorithm only reads attributes and `has_active_download()`, so a SimpleNamespace wired with
    a `tracked_anime_episode.tracked_anime.profile` chain is sufficient — no ORM/session involved.
    """
    def _make(*, profile, magnet_hash=None, episode_id=1, episode_part=0, episode_part_ceiling=0,
              version_number=1, release_group="GroupA", encoding=Encoding.HEVC, resolution=Resolution.P1080,
              source=VideoSource.CRUNCHYROLL, language_code="eng", repack_indicator=False, active_download=False):
        n = next(_ids)
        tracked_anime = SimpleNamespace(profile=profile)
        episode = SimpleNamespace(tracked_anime=tracked_anime)
        return SimpleNamespace(
            id=n,
            magnet_hash=magnet_hash or f"hash-{n}",
            tracked_anime_episode_id=episode_id,
            tracked_anime_episode=episode,
            episode_part=episode_part,
            episode_part_ceiling=episode_part_ceiling,
            version_number=version_number,
            release_group=release_group,
            encoding=encoding,
            resolution=resolution,
            source=source,
            language_code=language_code,
            repack_indicator=repack_indicator,
            has_active_download=lambda active=active_download: active,
        )
    return _make
