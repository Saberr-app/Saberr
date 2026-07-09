import pytest

from components.api_components.user_anime_list_api_component import UserAnimeListAPIComponent
from dto.anilist import AnilistAiringScheduleItem, AnilistAnime, AnilistUserList, AnilistUserListEntry


def _date_dict(date: tuple[int, int, int] | None) -> dict | None:
    if date is None:
        return None
    year, month, day = date
    return {"year": year, "month": month, "day": day}


def _make_anime(anime_id: int,
                title: str,
                season_year: int | None = None,
                season: str | None = None,
                episodes: int | None = None,
                anime_format: str | None = None,
                source: str | None = None,
                status: str = "FINISHED",
                synonyms: list[str] | None = None,
                time_until_airing: int | None = None) -> AnilistAnime:
    # english/romaji/native are kept identical so sorting is independent of the configured title language
    data = {
        "id": anime_id,
        "title": {"english": title, "romaji": title, "native": title},
        "season": season,
        "seasonYear": season_year,
        "episodes": episodes,
        "format": anime_format,
        "source": source,
        "status": status,
        "synonyms": synonyms or [],
    }
    if time_until_airing is not None:
        data["nextAiringEpisode"] = {"airingAt": time_until_airing, "episode": 1}
    return AnilistAnime.from_dict(data)


def _make_entry(anime_id: int,
                status: str = "COMPLETED",
                score: float = 0.0,
                progress: int = 0,
                repeat_count: int = 0,
                is_private: bool = False,
                started_at: tuple[int, int, int] | None = None,
                completed_at: tuple[int, int, int] | None = None,
                notes: str | None = None) -> AnilistUserListEntry:
    return AnilistUserListEntry.from_dict({
        "id": anime_id * 1000,
        "mediaId": anime_id,
        "status": status,
        "score": score,
        "progress": progress,
        "repeat": repeat_count,
        "private": is_private,
        "startedAt": _date_dict(started_at),
        "completedAt": _date_dict(completed_at),
        "notes": notes,
    })


def _make_airing(airing_at: int, episode: int, anilist_id: int) -> AnilistAiringScheduleItem:
    return AnilistAiringScheduleItem(airing_at=airing_at, episode=episode, anilist_id=anilist_id)


class _FakeListComponent:
    def __init__(self, user_list: AnilistUserList):
        self.user_list = user_list
        self.fetch_called = False
        self.fetch_full_anime_data_called = False
        self.update_calls: list[dict] = []
        self.delete_calls: list[int] = []
        self.update_return: AnilistUserListEntry | None = None

    async def get_user_anime_list(self, force_fetch: bool = False) -> AnilistUserList:
        return self.user_list

    async def fetch_user_anime_list(self, fetch_full_anime_data: bool = False) -> None:
        self.fetch_called = True
        self.fetch_full_anime_data_called = fetch_full_anime_data

    async def update_user_list_entry(self, **kwargs) -> AnilistUserListEntry:
        self.update_calls.append(kwargs)
        return self.update_return

    async def delete_user_list_entry(self, anilist_anime_id: int) -> None:
        self.delete_calls.append(anilist_anime_id)


class _FakeAnilistComponent:
    def __init__(self, anime_records: list[AnilistAnime], schedules: dict[int, list[AnilistAiringScheduleItem]]):
        self.anime_records = anime_records
        self.schedules = schedules
        self.record_calls: list[list[int]] = []
        self.schedule_calls: list[list[int]] = []

    async def get_anime_records(self, anilist_anime_ids: list[int]) -> list[AnilistAnime]:
        self.record_calls.append(anilist_anime_ids)
        wanted = set(anilist_anime_ids)
        return [anime for anime in self.anime_records if anime.id in wanted]


class _FakeAiringScheduleComponent:
    def __init__(self, schedules: dict[int, list[AnilistAiringScheduleItem]]):
        self.schedules = schedules
        self.status_map_calls: list[dict] = []

    async def get_future_anime_schedule_records_map(self,
                                                    anilist_id_status_map: dict,
                                                    filter_out_past: bool = True,
                                                    force_fetch: bool = False) -> dict[int, list]:
        self.status_map_calls.append(anilist_id_status_map)
        return {anilist_id: self.schedules.get(anilist_id, []) for anilist_id in anilist_id_status_map}


class _FakeTrackedAnimeComponent:
    async def get_tracked_anime_by_anilist_ids(self, anilist_ids, load_relations: bool = True) -> list:
        return []

    async def get_tracked_anime(self, anilist_id: int, load_relations: bool = True):
        return None


@pytest.fixture
def make_anime():
    return _make_anime


@pytest.fixture
def make_entry():
    return _make_entry


@pytest.fixture
def make_airing():
    return _make_airing


@pytest.fixture
def make_component():
    def _make(entries: list[AnilistUserListEntry],
              anime_records: list[AnilistAnime],
              schedules: dict[int, list[AnilistAiringScheduleItem]] | None = None) -> UserAnimeListAPIComponent:
        user_list = AnilistUserList.from_list_of_dict([entry.raw_data for entry in entries])
        component = UserAnimeListAPIComponent.__new__(UserAnimeListAPIComponent)  # bypass the heavy __init__
        component._anilist_list_component = _FakeListComponent(user_list)
        component._anilist_component = _FakeAnilistComponent(anime_records, schedules or {})
        component._anilist_airing_schedule_component = _FakeAiringScheduleComponent(schedules or {})
        component._tracked_anime_component = _FakeTrackedAnimeComponent()
        return component
    return _make
