from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from dto.anilist import AnilistAnimeMinimal


def _db_torrent(*, magnet_hash, parent_torrent_id=None, active_download=False):
    return SimpleNamespace(magnet_hash=magnet_hash, parent_torrent_id=parent_torrent_id,
                           has_active_download=lambda: active_download)


@dataclass
class Case:
    id: str
    db_torrents: list                # built lazily in the runner from specs
    expected_route: str | None       # 'preprocess' | 'processed' | None
    expected_parent_tracked: bool = False  # whether the parent is carried into _process_raw_torrents


# db torrents are described as specs; the runner materializes them keyed to the single raw torrent's hash
_SPEC_NONE = []
_SPEC_UNPROCESSED_PARENT = [dict(parent_torrent_id=None, active_download=False)]
_SPEC_PROCESSED_PARENT = [dict(parent_torrent_id=None, active_download=True),
                          dict(parent_torrent_id=1, active_download=False)]
_SPEC_NO_PARENT = [dict(parent_torrent_id=9, active_download=False)]


CASES = [
    Case(id="no db match routes to preprocess", db_torrents=_SPEC_NONE, expected_route="preprocess"),
    Case(id="unprocessed parent routes to preprocess and tracks the parent",
         db_torrents=_SPEC_UNPROCESSED_PARENT, expected_route="preprocess", expected_parent_tracked=True),
    Case(id="processed parent routes to processed populate",
         db_torrents=_SPEC_PROCESSED_PARENT, expected_route="processed"),
    Case(id="db rows without a parent are flagged and skipped",
         db_torrents=_SPEC_NO_PARENT, expected_route=None),
]

_COMPONENT = "components.operational_components.torrent_component.TorrentComponent"


def _wire(component, raw_torrent, db_torrents, mocker):
    component.get_torrents_by_hashes = AsyncMock(return_value=db_torrents)
    component._anilist_component.get_anime_multi_search_results = AsyncMock(
        return_value={raw_torrent.title_parts.search_title:
                      AnilistAnimeMinimal.from_dict({"id": 100, "title": {"romaji": "Match"}})})
    component._tracked_anime_component.get_tracked_anime_release_group_overrides_map = AsyncMock(return_value={})
    preprocess = mocker.patch(f"{_COMPONENT}._preprocess_raw_torrent", new=AsyncMock())
    populate_processed = mocker.patch(f"{_COMPONENT}._populate_processed_raw_torrent", new=AsyncMock())
    process = mocker.patch(f"{_COMPONENT}._process_raw_torrents", new=AsyncMock())
    return preprocess, populate_processed, process


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_populate_raw_torrents_data(case: Case, make_component, make_raw_torrent, mocker):
    raw_torrent = make_raw_torrent(magnet_hash="hash-A")
    db_torrents = [_db_torrent(magnet_hash="hash-A", **spec) for spec in case.db_torrents]

    component = make_component()
    preprocess, populate_processed, process = _wire(component, raw_torrent, db_torrents, mocker)

    await component.populate_raw_torrents_data(raw_torrents=[raw_torrent])

    if case.expected_route == "preprocess":
        preprocess.assert_awaited_once()
        populate_processed.assert_not_awaited()
        # the anilist search result is forwarded for matching
        assert preprocess.await_args.kwargs["anilist_anime_min"].id == 100
        parent_map = process.await_args.kwargs["hash_parent_db_torrent_map"]
        assert ("hash-A" in parent_map) == case.expected_parent_tracked
    elif case.expected_route == "processed":
        populate_processed.assert_awaited_once()
        preprocess.assert_not_awaited()
        # the parent (no parent_torrent_id) is passed; the child goes in other_db_torrents
        raw, parent, others = populate_processed.await_args.args
        assert parent.parent_torrent_id is None
        assert len(others) == 1
    else:
        preprocess.assert_not_awaited()
        populate_processed.assert_not_awaited()
        assert raw_torrent.notes[-1][1] is True


async def test_search_title_match_is_preferred_over_title(make_component, make_raw_torrent, make_title_parts, mocker):
    raw_torrent = make_raw_torrent(title_parts=make_title_parts(title="Show", search_title="Show Season 2"))
    component = make_component()
    component.get_torrents_by_hashes = AsyncMock(return_value=[])
    component._anilist_component.get_anime_multi_search_results = AsyncMock(return_value={
        "Show": AnilistAnimeMinimal.from_dict({"id": 1, "title": {"romaji": "Show"}}),
        "Show Season 2": AnilistAnimeMinimal.from_dict({"id": 2, "title": {"romaji": "Show S2"}}),
    })
    component._tracked_anime_component.get_tracked_anime_release_group_overrides_map = AsyncMock(return_value={})
    preprocess = mocker.patch(f"{_COMPONENT}._preprocess_raw_torrent", new=AsyncMock())
    mocker.patch(f"{_COMPONENT}._populate_processed_raw_torrent", new=AsyncMock())
    mocker.patch(f"{_COMPONENT}._process_raw_torrents", new=AsyncMock())

    await component.populate_raw_torrents_data(raw_torrents=[raw_torrent])

    # search_title ("Show Season 2") wins over the plain title ("Show")
    assert preprocess.await_args.kwargs["anilist_anime_min"].id == 2
