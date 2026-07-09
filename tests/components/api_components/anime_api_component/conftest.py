import pytest

from components.api_components.anime_api_component import AnimeAPIComponent
from components.service_components.anilist_component import AnilistComponent
from components.service_components.anilist_list_component import AnilistListComponent
from components.service_components.anilist_airing_schedule_component import AnilistAiringScheduleComponent
from components.operational_components.tracked_anime_component import TrackedAnimeComponent
from services.anilist_service import AnilistService


@pytest.fixture
def make_component():
    """An AnimeAPIComponent with its heavy __init__ bypassed.

    Sibling component/service methods are patched at class level per test (see `patch_async_returns`),
    so bare `__new__` instances are enough — the mocks ignore instance state.
    """
    def _make() -> AnimeAPIComponent:
        component = AnimeAPIComponent.__new__(AnimeAPIComponent)
        component._anilist_component = AnilistComponent.__new__(AnilistComponent)
        component._anilist_list_component = AnilistListComponent.__new__(AnilistListComponent)
        component._anilist_service = AnilistService.__new__(AnilistService)
        component._tracked_anime_component = TrackedAnimeComponent.__new__(TrackedAnimeComponent)
        component._anilist_airing_schedule_component = \
            AnilistAiringScheduleComponent.__new__(AnilistAiringScheduleComponent)
        return component
    return _make
