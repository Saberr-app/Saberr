from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from itertools import count
from unittest.mock import ANY

import pytest

from api.schemas.schedule_schemas import AiringScheduleListRequest
from common.exceptions import BadRequestException
from config import config
from constants import (AiringScheduleScope, AnilistAnimeSeason, AnilistAnimeStatus, AnilistAnimeUserStatus,
                       TorrentDownloadStatus, TrackedAnimeStatus)
from dto.anilist import AnilistAnime, AnilistAiringScheduleItem
from dto.orm_models import TrackedAnime, TrackedAnimeEpisode, Torrent, TorrentDownload
from components.api_components.schedule_api_component import ScheduleAPIComponent
from components.service_components.anilist_list_component import AnilistListComponent
from components.service_components.anilist_component import AnilistComponent
from components.service_components.anilist_airing_schedule_component import AnilistAiringScheduleComponent
from components.operational_components.tracked_anime_component import TrackedAnimeComponent
from services.anilist_service import AnilistService
from tests.support.builders import make_entry, make_user_list
from tests.support.mocks import patch_async_returns

_LIST_GET = "components.service_components.anilist_list_component.AnilistListComponent.get_user_anime_list"
_TRACKED_ALL = ("components.operational_components.tracked_anime_component"
                ".TrackedAnimeComponent.get_all_tracked_anime")
_ANIME_RECORDS = "components.service_components.anilist_component.AnilistComponent.get_anime_records"
_SCHEDULES = ("components.service_components.anilist_airing_schedule_component"
              ".AnilistAiringScheduleComponent.get_airing_schedules_in_range")

_DAY = datetime(2026, 6, 15, tzinfo=UTC)
_TS = TorrentDownloadStatus
_tracked_ids = count(1)


def _record(anilist_id: int, *, popularity: int | None = 50, season: str | None = "WINTER",
            season_year: int | None = 2026, status: str = "RELEASING") -> AnilistAnime:
    return AnilistAnime.from_dict({
        "id": anilist_id,
        "title": {"english": f"E{anilist_id}", "romaji": f"R{anilist_id}", "native": f"N{anilist_id}"},
        "popularity": popularity,
        "season": season,
        "seasonYear": season_year,
        "status": status,
    })


def _torrent(status: TorrentDownloadStatus | None) -> Torrent:
    torrent = Torrent()
    torrent.download = TorrentDownload(status=status) if status is not None else None
    return torrent


def _episode(episode_number: int, torrent_statuses: list[TorrentDownloadStatus | None]) -> TrackedAnimeEpisode:
    episode = TrackedAnimeEpisode(episode_number=episode_number)
    episode.torrents = [_torrent(status) for status in torrent_statuses]
    return episode


def _tracked(anilist_id: int, episodes: list[tuple[int, list]], *, tracked_id: int | None = None) -> TrackedAnime:
    tracked = TrackedAnime(anilist_id=anilist_id, romaji_title="R", status=TrackedAnimeStatus.ACTIVE,
                           from_episode=1, show_parent_directory="/a", show_folder_name="F")
    tracked.id = tracked_id if tracked_id is not None else next(_tracked_ids)
    tracked.episodes = [_episode(number, statuses) for number, statuses in episodes]
    return tracked


# default anime-list expectation for the single-anime download-status cases (tracked_id always 7 there)
def _anime_row(anilist_id=1, popularity=50, season=AnilistAnimeSeason.WINTER, season_year=2026,
               status=AnilistAnimeStatus.RELEASING, user_status=None, tracked_id=7):
    return (anilist_id, popularity, season, season_year, status, user_status, tracked_id)


@dataclass
class Case:
    id: str
    request_kwargs: dict
    schedules: dict[int, list[tuple[int, int]]] = field(default_factory=dict)
    records: list[AnilistAnime] = field(default_factory=list)
    tracked: list[TrackedAnime] = field(default_factory=list)
    user_entries: list = field(default_factory=list)
    anilist_user_token: str | None = None
    expected_schedule: list[tuple] = field(default_factory=list)
    expected_anime: list[tuple] = field(default_factory=list)
    expected_window: tuple[datetime, datetime] | None = None
    expected_exception: type[Exception] | None = None


def _status_case(case_id: str, torrent_statuses: list, expected_status, *, episode_number: int = 5) -> Case:
    """Single anime (id 1), one airing event for episode 5; vary the matched episode's torrents."""
    return Case(
        id=case_id,
        request_kwargs=dict(day=_DAY, scope=[AiringScheduleScope.USER_TRACKING]),
        schedules={1: [(5, 1000)]},
        records=[_record(1)],
        tracked=[_tracked(1, [(episode_number, torrent_statuses)], tracked_id=7)],
        expected_schedule=[(10005, 1, 5, 1000, expected_status)],
        expected_anime=[_anime_row()],
    )


CASES = [
    # download-status priority: best (most-progressed) status across the episode's torrents wins
    _status_case("processing-beats-pending", [_TS.PENDING, _TS.PROCESSING], _TS.PROCESSING),
    _status_case("downloaded-beats-downloading", [_TS.DOWNLOADING, _TS.DOWNLOADED], _TS.DOWNLOADED),
    _status_case("pending-beats-failed", [_TS.FAILED_DOWNLOAD, _TS.PENDING], _TS.PENDING),
    _status_case("processed-beats-deleted", [_TS.DELETED, _TS.PROCESSED], _TS.PROCESSED),
    _status_case("failed-processing-beats-failed-download", [_TS.FAILED_DOWNLOAD, _TS.FAILED_PROCESSING],
                 _TS.FAILED_PROCESSING),
    # DELETED/DISCARDED collapse to a null status
    _status_case("deleted-and-discarded-collapse-null", [_TS.DELETED, _TS.DISCARDED], None),
    _status_case("single-discarded-null", [_TS.DISCARDED], None),
    # no resolvable download -> null
    _status_case("no-torrents-null", [], None),
    _status_case("torrent-without-download-null", [None], None),
    _status_case("episode-number-mismatch-null", [_TS.PROCESSED], None, episode_number=6),
    Case(id="no-tracked-anime-null",
         request_kwargs=dict(day=_DAY, scope=[AiringScheduleScope.USER_TRACKING]),
         schedules={1: [(5, 1000)]}, records=[_record(1)], tracked=[],
         expected_schedule=[(10005, 1, 5, 1000, None)],
         expected_anime=[_anime_row(tracked_id=None)]),

    # metadata mapping
    Case(id="popularity-null-defaults-zero",
         request_kwargs=dict(day=_DAY, scope=[AiringScheduleScope.USER_TRACKING]),
         schedules={1: [(5, 1000)]}, records=[_record(1, popularity=None)],
         tracked=[_tracked(1, [(5, [_TS.PROCESSED])], tracked_id=7)],
         expected_schedule=[(10005, 1, 5, 1000, _TS.PROCESSED)],
         expected_anime=[_anime_row(popularity=0)]),
    Case(id="user-list-status-mapped",
         request_kwargs=dict(day=_DAY, scope=[AiringScheduleScope.USER_WATCHING]),
         anilist_user_token="token", user_entries=[make_entry(1, status="CURRENT")],
         schedules={1: [(5, 1000)]}, records=[_record(1)],
         tracked=[_tracked(1, [(5, [_TS.PROCESSED])], tracked_id=7)],
         expected_schedule=[(10005, 1, 5, 1000, _TS.PROCESSED)],
         expected_anime=[_anime_row(user_status=AnilistAnimeUserStatus.CURRENT)]),

    # anime present in schedules but missing a metadata record is dropped entirely
    Case(id="schedule-without-record-skipped",
         request_kwargs=dict(day=_DAY, scope=[AiringScheduleScope.USER_TRACKING]),
         schedules={1: [(5, 1000)], 2: [(3, 2000)]}, records=[_record(1)],
         tracked=[_tracked(1, [(5, [_TS.PROCESSED])], tracked_id=7)],
         expected_schedule=[(10005, 1, 5, 1000, _TS.PROCESSED)],
         expected_anime=[_anime_row()]),

    # multiple anime / episodes: per-episode status resolution and id = anilist_id * 10000 + episode
    Case(id="multiple-anime-and-episodes",
         request_kwargs=dict(day=_DAY, scope=[AiringScheduleScope.USER_TRACKING]),
         schedules={1: [(1, 100), (2, 200)], 2: [(1, 300)]},
         records=[_record(1), _record(2)],
         tracked=[_tracked(1, [(1, [_TS.PROCESSED]), (2, [_TS.DOWNLOADING])], tracked_id=7),
                  _tracked(2, [(1, [_TS.DISCARDED])], tracked_id=8)],
         expected_schedule=[(10001, 1, 1, 100, _TS.PROCESSED),
                            (10002, 1, 2, 200, _TS.DOWNLOADING),
                            (20001, 2, 1, 300, None)],
         expected_anime=[_anime_row(anilist_id=1, tracked_id=7),
                         _anime_row(anilist_id=2, tracked_id=8)]),

    # request window selection forwarded to the schedule lookup
    Case(id="day-window",
         request_kwargs=dict(day=_DAY, scope=[AiringScheduleScope.USER_TRACKING]),
         expected_window=(_DAY, _DAY + timedelta(days=1))),
    Case(id="week-window",
         request_kwargs=dict(week=_DAY, scope=[AiringScheduleScope.USER_TRACKING]),
         expected_window=(_DAY, _DAY + timedelta(days=7))),
    Case(id="month-window",
         request_kwargs=dict(month=datetime(2026, 1, 15, tzinfo=UTC), scope=[AiringScheduleScope.USER_TRACKING]),
         expected_window=(datetime(2026, 1, 15, tzinfo=UTC), datetime(2026, 2, 15, tzinfo=UTC))),
    Case(id="month-window-december-rollover",
         request_kwargs=dict(month=datetime(2026, 12, 10, tzinfo=UTC), scope=[AiringScheduleScope.USER_TRACKING]),
         expected_window=(datetime(2026, 12, 10, tzinfo=UTC), datetime(2027, 1, 10, tzinfo=UTC))),

    # validation
    Case(id="no-window-raises",
         request_kwargs=dict(scope=[AiringScheduleScope.USER_TRACKING]),
         expected_exception=BadRequestException),
    Case(id="no-scope-raises",
         request_kwargs=dict(day=_DAY, scope=[]),
         expected_exception=BadRequestException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_airing_schedule(case: Case, mocker):
    config.user_settings.anilist_user_token = case.anilist_user_token
    schedules = {anilist_id: [AnilistAiringScheduleItem(anilist_id=anilist_id, episode=episode, airing_at=airing_at)
                              for episode, airing_at in items]
                 for anilist_id, items in case.schedules.items()}
    mocks = patch_async_returns(mocker, {
        _LIST_GET: make_user_list(case.user_entries),
        _TRACKED_ALL: case.tracked,
        _ANIME_RECORDS: case.records,
        _SCHEDULES: schedules,
    })
    component = ScheduleAPIComponent.__new__(ScheduleAPIComponent)
    component._anilist_list_component = AnilistListComponent.__new__(AnilistListComponent)
    component._anilist_component = AnilistComponent.__new__(AnilistComponent)
    component._anilist_service = AnilistService.__new__(AnilistService)
    component._tracked_anime_component = TrackedAnimeComponent.__new__(TrackedAnimeComponent)
    component._anilist_airing_schedule_component = \
        AnilistAiringScheduleComponent.__new__(AnilistAiringScheduleComponent)
    request = AiringScheduleListRequest(**case.request_kwargs)

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await component.get_airing_schedule(request)
        return

    response = await component.get_airing_schedule(request)

    assert all(item.title is None for item in response.airing_schedule)
    actual_schedule = sorted((item.id, item.anilist_id, item.episode, item.airing_at, item.download_status)
                             for item in response.airing_schedule)
    assert actual_schedule == sorted(case.expected_schedule)
    actual_anime = sorted((a.anilist_id, a.popularity, a.season, a.season_year, a.status,
                           a.user_list_status, a.tracked_anime_id) for a in response.anime)
    assert actual_anime == sorted(case.expected_anime)

    if case.expected_window is not None:
        mocks[_SCHEDULES].assert_awaited_once_with(
            from_date=case.expected_window[0], to_date=case.expected_window[1],
            anilist_anime_ids=ANY, force_fetch=request.force_refresh)