from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from common.exceptions import AnilistRelationsEpisodeCountMismatch
from constants import TrackedAnimeStatus
from dto.anilist import AnilistAnimeMinimal

_RESOLVE = "app_state.anime_relations.resolve_anime"


def _tracked(anilist_id, status=TrackedAnimeStatus.ACTIVE):
    return SimpleNamespace(anilist_id=anilist_id, status=status,
                           english_title="English", romaji_title="Romaji", native_title="Native")


def _prefs(*, tracked_anime, offset):
    return SimpleNamespace(tracked_anime=tracked_anime, episode_number_offset=offset)


@dataclass
class Case:
    id: str
    episode_number: int = 5
    has_anilist_match: bool = True       # whether the torrent title resolved to an Anilist anime
    overriding: dict | None = None       # {status, offset, anilist_id}
    resolve: object = None               # None => echo input; (id, ep) => remap; "raises" => mismatch
    # expectations
    expected_to_process: bool = False
    expected_require_identifying: bool = False
    expected_error_note: bool = False
    expected_anime_id: int | None = None      # anilist_anime_min.id after the call
    expected_episode_number: int | None = None
    expected_relations_id: int | None = None  # t_relations_anilist_id
    expected_tracked_id: int | None = None    # t_tracked_anilist_id


CASES = [
    Case(id="no anilist match and no override fails to identify",
         has_anilist_match=False, expected_require_identifying=True, expected_error_note=True),
    Case(id="no anilist match, override offset not below episode number",
         has_anilist_match=False, episode_number=5,
         overriding=dict(status=TrackedAnimeStatus.ACTIVE, offset=5, anilist_id=200),
         expected_require_identifying=True, expected_error_note=True),
    Case(id="no anilist match, override applies offset and proceeds",
         has_anilist_match=False, episode_number=5,
         overriding=dict(status=TrackedAnimeStatus.ACTIVE, offset=2, anilist_id=200),
         expected_to_process=True, expected_anime_id=200, expected_episode_number=3, expected_tracked_id=200),
    Case(id="anilist match overridden by active release-group preference",
         has_anilist_match=True, episode_number=5,
         overriding=dict(status=TrackedAnimeStatus.ACTIVE, offset=2, anilist_id=200),
         expected_to_process=True, expected_anime_id=200, expected_episode_number=3, expected_tracked_id=200),
    Case(id="anilist match resolves to same id and proceeds",
         has_anilist_match=True, expected_to_process=True, expected_anime_id=100, expected_episode_number=5),
    Case(id="anilist match remapped to a different id defers to relations",
         has_anilist_match=True, resolve=(300, 4),
         expected_to_process=True, expected_episode_number=4, expected_relations_id=300),
    Case(id="resolve raises episode count mismatch",
         has_anilist_match=True, resolve="raises",
         expected_require_identifying=True, expected_error_note=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test__preprocess_raw_torrent(case: Case, make_component, make_raw_torrent, make_title_parts, mocker):
    raw_torrent = make_raw_torrent(title_parts=make_title_parts(episode_number=case.episode_number))
    anilist_anime_min = (AnilistAnimeMinimal.from_dict({"id": 100, "title": {"romaji": "Match"}})
                         if case.has_anilist_match else None)

    overriding = None
    if case.overriding:
        overriding = _prefs(tracked_anime=_tracked(case.overriding["anilist_id"], case.overriding["status"]),
                            offset=case.overriding["offset"])

    if case.resolve == "raises":
        mocker.patch(_RESOLVE, side_effect=AnilistRelationsEpisodeCountMismatch())
    elif case.resolve is None:
        mocker.patch(_RESOLVE, side_effect=lambda *, original_anilist_id, original_episode_number:
                     (original_anilist_id, original_episode_number))
    else:
        mocker.patch(_RESOLVE, return_value=case.resolve)

    component = make_component()
    await component._preprocess_raw_torrent(raw_torrent=raw_torrent, anilist_anime_min=anilist_anime_min,
                                            overriding_release_groups_preferences=overriding)

    assert raw_torrent.t_to_process == case.expected_to_process
    assert raw_torrent.require_identifying_data_on_override == case.expected_require_identifying
    if case.expected_error_note:
        assert raw_torrent.notes[-1][1] is True
    if case.expected_anime_id is not None:
        assert raw_torrent.anilist_anime_min.id == case.expected_anime_id
    if case.expected_episode_number is not None:
        assert raw_torrent.anilist_episode_number == case.expected_episode_number
    assert raw_torrent.t_relations_anilist_id == case.expected_relations_id
    assert raw_torrent.t_tracked_anilist_id == case.expected_tracked_id
