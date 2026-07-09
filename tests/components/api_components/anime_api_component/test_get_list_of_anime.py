from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from api.schemas.anime_schemas import AnimeListRequest
from config import config
from constants import TrackedAnimeStatus
from dto.anilist import AnilistAnime
from tests.support.builders import make_anime, make_entry, make_user_list
from tests.support.mocks import patch_async_returns

_FILTERS = "components.service_components.anilist_component.AnilistComponent.get_anime_with_filters"
_AIRING_MAP = ("components.service_components.anilist_airing_schedule_component"
               ".AnilistAiringScheduleComponent.get_future_anime_schedule_records_map")
_LIST = "components.service_components.anilist_list_component.AnilistListComponent.get_user_anime_list"
_TRACKED = ("components.operational_components.tracked_anime_component"
            ".TrackedAnimeComponent.get_tracked_anime_by_anilist_ids")
_TVDB = "app_state.anime_relations.get_anilist_id_tvdb_series_id"


def _two_anime() -> list[AnilistAnime]:
    return [make_anime(1, "First"), make_anime(2, "Second")]


@dataclass
class Case:
    id: str
    anime: list[AnilistAnime] = field(default_factory=_two_anime)
    tracked: list = field(default_factory=list)
    authenticated: bool = False
    entries: list = field(default_factory=list)
    expected_ids: list[int] = field(default_factory=lambda: [1, 2])
    expected_tracked_ids: dict | None = None     # {anime_id: tracked_anime_id}
    expected_user_entry: dict | None = None      # {anime_id: progress}


CASES = [
    Case(id="returns items in the order from the filters query", expected_ids=[1, 2]),
    Case(id="maps tracked anime ids",
         tracked=[SimpleNamespace(anilist_id=2, id=55, status=TrackedAnimeStatus.ACTIVE)],
         expected_tracked_ids={1: None, 2: 55}),
    Case(id="attaches user entries when authenticated",
         anime=[make_anime(1, "First")], authenticated=True,
         entries=[make_entry(1, status="COMPLETED", progress=12)],
         expected_ids=[1], expected_user_entry={1: 12}),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_list_of_anime(case: Case, make_component, mocker):
    if case.authenticated:
        config.user_settings.anilist_user_token = "token"
    patch_async_returns(mocker, {
        _FILTERS: case.anime,
        _AIRING_MAP: {},
        _LIST: make_user_list(case.entries),
        _TRACKED: case.tracked,
        _TVDB: None,
    })

    response = await make_component().get_list_of_anime(AnimeListRequest())

    assert [item.id for item in response.anime] == case.expected_ids
    by_id = {item.id: item for item in response.anime}
    if case.expected_tracked_ids is not None:
        assert {anime_id: by_id[anime_id].tracked_anime_id
                for anime_id in case.expected_tracked_ids} == case.expected_tracked_ids
    if case.expected_user_entry is not None:
        for anime_id, progress in case.expected_user_entry.items():
            assert by_id[anime_id].user_entry.progress == progress
    else:
        assert all(item.user_entry is None for item in response.anime)
