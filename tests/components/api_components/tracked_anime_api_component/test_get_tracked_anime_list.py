from dataclasses import dataclass

import pytest

from components.api_components.tracked_anime_api_component import TrackedAnimeAPIComponent

_TA = "components.operational_components.tracked_anime_component.TrackedAnimeComponent"
_ANILIST = "components.service_components.anilist_component.AnilistComponent"
_AIRING = ("components.service_components.anilist_airing_schedule_component"
           ".AnilistAiringScheduleComponent")
_MODULE = "components.api_components.tracked_anime_api_component"


@dataclass
class Case:
    id: str
    anilist_id: int
    expected_anilist_ids: list[int]


CASES = [
    Case(id="includes only hydrated active anime", anilist_id=8511, expected_anilist_ids=[8511]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_tracked_anime_list(case: Case, make_anime, make_full_tracked_anime, mocker):
    anime = make_anime(anilist_id=case.anilist_id)
    tracked = make_full_tracked_anime(anilist_id=case.anilist_id)

    mocker.patch(f"{_TA}.get_all_tracked_anime", return_value=[tracked])
    mocker.patch(f"{_ANILIST}.get_anime_records", return_value=[anime])
    mocker.patch(f"{_AIRING}.get_future_anime_schedule_records_map", return_value={})
    mocker.patch(f"{_MODULE}.anime_relations.get_anilist_id_tvdb_series_id", return_value=None)

    result = await TrackedAnimeAPIComponent().get_tracked_anime_list()

    assert [item.anilist_id for item in result.tracked_anime] == case.expected_anilist_ids
