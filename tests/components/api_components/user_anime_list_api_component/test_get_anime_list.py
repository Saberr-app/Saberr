from dataclasses import dataclass, field

import pytest

from api.schemas.user_anime_list_schemas import UserAnimeListRequest
from common.exceptions import FailedDependencyException
from constants import SortDirection
from dto.anilist import AnilistAiringScheduleItem, AnilistAnime, AnilistUserListEntry
from components.api_components.user_anime_list_api_component import UserAnimeListAPIComponent
from components.service_components.anilist_list_component import AnilistListComponent
from components.service_components.anilist_component import AnilistComponent
from components.service_components.anilist_airing_schedule_component import AnilistAiringScheduleComponent
from components.operational_components.tracked_anime_component import TrackedAnimeComponent
from tests.support.builders import make_anime, make_entry, make_user_list
from tests.support.mocks import patch_async_returns

_SortBy = UserAnimeListRequest.UserAnimeListSortBy

# dotted targets patched per test (async sibling component methods + the anime_relations global)
_LIST_FETCH = "components.service_components.anilist_list_component.AnilistListComponent.fetch_user_anime_list"
_LIST_GET = "components.service_components.anilist_list_component.AnilistListComponent.get_user_anime_list"
_ANIME_RECORDS = "components.service_components.anilist_component.AnilistComponent.get_anime_records"
_AIRING_MAP = ("components.service_components.anilist_airing_schedule_component"
               ".AnilistAiringScheduleComponent.get_future_anime_schedule_records_map")
_TRACKED = ("components.operational_components.tracked_anime_component"
            ".TrackedAnimeComponent.get_tracked_anime_by_anilist_ids")
_TVDB = "app_state.anime_relations.get_anilist_id_tvdb_series_id"


def _dataset_anime() -> list[AnilistAnime]:
    # title order Alpha(2) < Beta(1) < Gamma(3); anime 3 has null season/episodes/format/source/airing
    return [
        make_anime(1, "Beta", season_year=2021, season="FALL", episodes=12, anime_format="TV",
                   source="MANGA", status="FINISHED", synonyms=["b-alias"], airing_at=1000),
        make_anime(2, "Alpha", season_year=2021, season="WINTER", episodes=24, anime_format="MOVIE",
                   source="ORIGINAL", status="RELEASING", airing_at=500),
        make_anime(3, "Gamma", status="NOT_YET_RELEASED"),
    ]


def _dataset_entries() -> list[AnilistUserListEntry]:
    return [
        make_entry(1, status="COMPLETED", score=9.0, progress=12, repeat_count=1,
                   started_at=(2020, 1, 2), completed_at=(2021, 3, 4)),
        make_entry(2, status="CURRENT", score=7.0, progress=5, repeat_count=0, started_at=(2019, 5, 6)),
        make_entry(3, status="PLANNING", score=8.0, progress=0, repeat_count=2),
    ]


@dataclass
class Case:
    id: str
    request_kwargs: dict
    entries: list[AnilistUserListEntry] = field(default_factory=_dataset_entries)
    anime_records: list[AnilistAnime] = field(default_factory=_dataset_anime)
    airing_map: dict[int, list[AnilistAiringScheduleItem]] = field(default_factory=dict)
    expected_ids: list[int] | None = None
    expected_exception: type[Exception] | None = None


def _sort(sort_by, direction, expected, _id):
    return Case(id=_id, request_kwargs=dict(sort_by=sort_by, sort_direction=direction),
                expected_ids=expected)


# entries whose sort value is None always land last, regardless of direction
CASES = [
    _sort(_SortBy.TITLE, SortDirection.ASC, [2, 1, 3], "title-asc"),
    _sort(_SortBy.TITLE, SortDirection.DESC, [3, 1, 2], "title-desc"),
    _sort(_SortBy.SEASON_AND_YEAR, SortDirection.ASC, [2, 1, 3], "season-asc"),
    _sort(_SortBy.SEASON_AND_YEAR, SortDirection.DESC, [1, 2, 3], "season-desc"),
    _sort(_SortBy.EPISODES, SortDirection.ASC, [1, 2, 3], "episodes-asc"),
    _sort(_SortBy.EPISODES, SortDirection.DESC, [2, 1, 3], "episodes-desc"),
    _sort(_SortBy.PROGRESS, SortDirection.ASC, [3, 2, 1], "progress-asc"),
    _sort(_SortBy.PROGRESS, SortDirection.DESC, [1, 2, 3], "progress-desc"),
    _sort(_SortBy.SCORE, SortDirection.ASC, [2, 3, 1], "score-asc"),
    _sort(_SortBy.SCORE, SortDirection.DESC, [1, 3, 2], "score-desc"),
    _sort(_SortBy.STATUS, SortDirection.ASC, [1, 2, 3], "status-asc"),
    _sort(_SortBy.STATUS, SortDirection.DESC, [3, 2, 1], "status-desc"),
    _sort(_SortBy.FORMAT, SortDirection.ASC, [2, 1, 3], "format-asc"),
    _sort(_SortBy.FORMAT, SortDirection.DESC, [1, 2, 3], "format-desc"),
    _sort(_SortBy.SOURCE, SortDirection.ASC, [1, 2, 3], "source-asc"),
    _sort(_SortBy.SOURCE, SortDirection.DESC, [2, 1, 3], "source-desc"),
    _sort(_SortBy.AIRING_STATUS, SortDirection.ASC, [1, 3, 2], "airing-status-asc"),
    _sort(_SortBy.AIRING_STATUS, SortDirection.DESC, [2, 3, 1], "airing-status-desc"),
    _sort(_SortBy.REPEAT_COUNT, SortDirection.ASC, [2, 1, 3], "repeat-asc"),
    _sort(_SortBy.REPEAT_COUNT, SortDirection.DESC, [3, 1, 2], "repeat-desc"),
    _sort(_SortBy.STARTED_AT, SortDirection.ASC, [2, 1, 3], "started-asc"),
    _sort(_SortBy.STARTED_AT, SortDirection.DESC, [1, 2, 3], "started-desc"),
    # only anime 1 has a completed_at; the rest keep title order at the end
    _sort(_SortBy.COMPLETED_AT, SortDirection.ASC, [1, 2, 3], "completed-asc"),
    _sort(_SortBy.COMPLETED_AT, SortDirection.DESC, [1, 2, 3], "completed-desc"),
    _sort(_SortBy.TIME_UNTIL_AIRING, SortDirection.ASC, [2, 1, 3], "time-until-airing-asc"),
    _sort(_SortBy.TIME_UNTIL_AIRING, SortDirection.DESC, [1, 2, 3], "time-until-airing-desc"),
    Case(id="query matches titles",
         request_kwargs=dict(query="alpha", sort_by=_SortBy.TITLE), expected_ids=[2]),
    Case(id="query matches synonyms",
         request_kwargs=dict(query="b-alias", sort_by=_SortBy.TITLE), expected_ids=[1]),
    Case(id="statuses filter",
         request_kwargs=dict(statuses=["CURRENT", "PLANNING"], sort_by=_SortBy.TITLE),
         expected_ids=[3, 2]),
    Case(id="season filter",
         request_kwargs=dict(season="FALL", sort_by=_SortBy.TITLE), expected_ids=[1]),
    Case(id="season_year filter",
         request_kwargs=dict(season_year=2021, sort_by=_SortBy.TITLE, sort_direction=SortDirection.ASC),
         expected_ids=[2, 1]),
    Case(id="pagination applies after sort",
         request_kwargs=dict(sort_by=_SortBy.TITLE, sort_direction=SortDirection.ASC, offset=1, limit=1),
         expected_ids=[1]),
    Case(id="missing anime metadata raises BadGateway",
         request_kwargs=dict(),
         entries=[make_entry(99)], anime_records=[],
         expected_exception=FailedDependencyException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_anime_list(case: Case, mocker):
    patch_async_returns(mocker, {
        _LIST_FETCH: None,
        _LIST_GET: make_user_list(case.entries),
        _ANIME_RECORDS: case.anime_records,
        _AIRING_MAP: case.airing_map,
        _TRACKED: [],
        _TVDB: None,
    })
    # Bypass the heavy __init__ (it constructs real AnilistService/SettingsComponent). The sibling
    # methods are patched at class level, so bare instances are sufficient — the mocks ignore
    # instance state.
    component = UserAnimeListAPIComponent.__new__(UserAnimeListAPIComponent)
    component._anilist_list_component = AnilistListComponent.__new__(AnilistListComponent)
    component._anilist_component = AnilistComponent.__new__(AnilistComponent)
    component._anilist_airing_schedule_component = \
        AnilistAiringScheduleComponent.__new__(AnilistAiringScheduleComponent)
    component._tracked_anime_component = TrackedAnimeComponent.__new__(TrackedAnimeComponent)
    request = UserAnimeListRequest(**case.request_kwargs)

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await component.get_anime_list(request)
        return

    response = await component.get_anime_list(request)
    assert [item.anime.id for item in response.anime_list] == case.expected_ids
