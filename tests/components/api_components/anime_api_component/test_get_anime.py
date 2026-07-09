from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from common.exceptions import NotFoundException
from config import config
from constants import TrackedAnimeStatus
from dto.anilist import AnilistAnime, AnilistAiringScheduleItem
from tests.support.builders import make_anime, make_airing, make_entry
from tests.support.mocks import patch_async_returns

_GET_ANIME = "components.service_components.anilist_component.AnilistComponent.get_anime"
_AIRING_MAP = ("components.service_components.anilist_airing_schedule_component"
               ".AnilistAiringScheduleComponent.get_future_anime_schedule_records_map")
_LIST_ENTRY = ("components.service_components.anilist_list_component"
               ".AnilistListComponent.get_user_anime_list_entry")
_TRACKED = ("components.operational_components.tracked_anime_component"
            ".TrackedAnimeComponent.get_tracked_anime")
_TVDB = "app_state.anime_relations.get_anilist_id_tvdb_series_id"


@dataclass
class Case:
    id: str
    anime: AnilistAnime | None = field(default_factory=lambda: make_anime(42, "Some Title"))
    airing: list[AnilistAiringScheduleItem] = field(default_factory=list)
    authenticated: bool = False
    user_entry: object = None
    tracked: object = None
    tvdb_series_id: int | None = None
    expected_exception: type[Exception] | None = None
    expected_tracked_anime_id: int | None = None
    expected_tvdb_series_id: int | None = None
    expected_next_airing_episode: int | None = None
    expected_has_user_entry: bool = False


CASES = [
    Case(id="returns the anime item", tvdb_series_id=7, expected_tvdb_series_id=7),
    Case(id="picks the earliest airing episode",
         airing=[make_airing(airing_at=2000, episode=3, anilist_id=42),
                 make_airing(airing_at=1000, episode=2, anilist_id=42)],
         expected_next_airing_episode=2),
    Case(id="includes the tracked anime id",
         tracked=SimpleNamespace(id=99, status=TrackedAnimeStatus.ACTIVE), expected_tracked_anime_id=99),
    Case(id="non-active tracked anime is not surfaced",
         tracked=SimpleNamespace(id=99, status=TrackedAnimeStatus.ARCHIVED), expected_tracked_anime_id=None),
    Case(id="includes the user entry when authenticated",
         authenticated=True, user_entry=make_entry(42, status="CURRENT", progress=5, score=8.0),
         expected_has_user_entry=True),
    Case(id="missing anime raises NotFound", anime=None, expected_exception=NotFoundException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_anime(case: Case, make_component, mocker):
    if case.authenticated:
        config.user_settings.anilist_user_token = "token"
    patch_async_returns(mocker, {
        _GET_ANIME: case.anime,
        _AIRING_MAP: {42: case.airing} if case.airing else {},
        _LIST_ENTRY: case.user_entry,
        _TRACKED: case.tracked,
        _TVDB: case.tvdb_series_id,
    })

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await make_component().get_anime(anilist_id=42)
        return

    result = await make_component().get_anime(anilist_id=42)

    assert result.id == 42
    assert result.tvdb_series_id == case.expected_tvdb_series_id
    assert result.tracked_anime_id == case.expected_tracked_anime_id
    if case.expected_next_airing_episode is None:
        assert result.next_airing_episode is None
    else:
        assert result.next_airing_episode.episode == case.expected_next_airing_episode
    assert (result.user_entry is not None) == case.expected_has_user_entry
