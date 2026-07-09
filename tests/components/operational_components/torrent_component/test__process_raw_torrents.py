from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from constants import TrackedAnimeStatus
from dto.anilist import AnilistAnimeMinimal

_REPO = "repositories.torrent_repositories.torrent_repo.TorrentRepo"


def _tracked(anilist_id, status=TrackedAnimeStatus.ACTIVE, from_episode=1):
    return SimpleNamespace(anilist_id=anilist_id, status=status, from_episode=from_episode)


@dataclass
class Case:
    id: str
    episode_number: int = 5
    relations_id: int | None = None      # t_relations_anilist_id; override anime resolved to this id
    relations_resolved: bool = True      # whether get_anime_records returns the override anime
    tracked: dict | None = None          # {status, from_episode} for the final anilist id (None => not tracked)
    auto_discard: bool = False
    has_db_torrent: bool = False
    db_discarded: bool = False
    # expectations
    expected_repo: str | None = None     # 'create' | 'update' | None
    expected_not_tracked: bool = False
    expected_require_identifying: bool = False
    expected_discarded: bool = False
    expected_anime_id: int | None = None


CASES = [
    Case(id="not tracked requires identifying and is skipped",
         tracked=None, expected_repo=None, expected_not_tracked=True, expected_require_identifying=True),
    Case(id="archived tracked anime is skipped",
         tracked=dict(status=TrackedAnimeStatus.ARCHIVED, from_episode=1),
         expected_repo=None, expected_not_tracked=True),
    Case(id="episode below tracked range is skipped",
         episode_number=5, tracked=dict(status=TrackedAnimeStatus.ACTIVE, from_episode=10),
         expected_repo=None, expected_not_tracked=True),
    Case(id="active tracked anime without a db torrent creates one",
         tracked=dict(status=TrackedAnimeStatus.ACTIVE, from_episode=1),
         expected_repo="create", expected_anime_id=100),
    Case(id="auto-discard episode is created discarded",
         tracked=dict(status=TrackedAnimeStatus.ACTIVE, from_episode=1), auto_discard=True,
         expected_repo="create", expected_discarded=True),
    Case(id="existing db torrent takes the update path",
         tracked=dict(status=TrackedAnimeStatus.ACTIVE, from_episode=1), has_db_torrent=True,
         expected_repo="update"),
    Case(id="db torrent discard propagates on update",
         tracked=dict(status=TrackedAnimeStatus.ACTIVE, from_episode=1), has_db_torrent=True, db_discarded=True,
         expected_repo="update", expected_discarded=True),
    Case(id="relations override remaps to the relations anime then creates",
         relations_id=300, relations_resolved=True,
         tracked=dict(status=TrackedAnimeStatus.ACTIVE, from_episode=1),
         expected_repo="create", expected_anime_id=300),
    Case(id="relations override that cannot be resolved requires identifying",
         relations_id=300, relations_resolved=False,
         expected_repo=None, expected_require_identifying=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test__process_raw_torrents(case: Case, make_component, make_raw_torrent, make_title_parts, mocker):
    raw_torrent = make_raw_torrent(title_parts=make_title_parts(episode_number=case.episode_number))
    raw_torrent.anilist_anime_min = AnilistAnimeMinimal.from_dict({"id": 100, "title": {"romaji": "Match"}})
    raw_torrent.anilist_episode_number = case.episode_number
    raw_torrent.t_relations_anilist_id = case.relations_id

    final_id = case.relations_id if (case.relations_id and case.relations_resolved) else 100

    component = make_component()
    tracked = _tracked(final_id, **case.tracked) if case.tracked else None
    component._tracked_anime_component.get_tracked_anime_by_anilist_ids = AsyncMock(
        return_value=[tracked] if tracked else [])
    override_anime = SimpleNamespace(id=case.relations_id, english_title="E", romaji_title="R", native_title="N")
    component._anilist_component.get_anime_records = AsyncMock(
        return_value=[override_anime] if (case.relations_id and case.relations_resolved) else [])
    episode = SimpleNamespace(id=555, auto_discard=case.auto_discard)
    component._tracked_anime_episode_component.get_or_create_tracked_anime_episode = AsyncMock(return_value=episode)

    repo_create = mocker.patch(f"{_REPO}.create_torrent", return_value=SimpleNamespace(id=10))
    repo_bulk_update = mocker.patch(f"{_REPO}.bulk_update_torrents")

    hash_parent_db_torrent_map = {}
    if case.has_db_torrent:
        hash_parent_db_torrent_map[raw_torrent.nyaa_item.magnet_hash] = SimpleNamespace(id=77,
                                                                                        discarded=case.db_discarded)

    await component._process_raw_torrents(raw_torrents=[raw_torrent],
                                          hash_parent_db_torrent_map=hash_parent_db_torrent_map)

    assert raw_torrent.not_tracked == case.expected_not_tracked
    assert raw_torrent.require_identifying_data_on_override == case.expected_require_identifying

    if case.expected_repo == "create":
        repo_create.assert_awaited_once()
        assert repo_bulk_update.await_args.kwargs["data"] == []
        assert raw_torrent.discarded == case.expected_discarded
        assert raw_torrent.db_episode_id == episode.id
    elif case.expected_repo == "update":
        repo_create.assert_not_awaited()
        assert len(repo_bulk_update.await_args.kwargs["data"]) == 1
        assert raw_torrent.discarded == case.expected_discarded
    else:
        repo_create.assert_not_awaited()
        assert repo_bulk_update.await_args.kwargs["data"] == []

    if case.expected_anime_id is not None:
        assert raw_torrent.anilist_anime_min.id == case.expected_anime_id
