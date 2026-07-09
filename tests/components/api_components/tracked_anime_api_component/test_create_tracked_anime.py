from dataclasses import dataclass

import pytest

from config import config
from components.api_components.tracked_anime_api_component import TrackedAnimeAPIComponent
from constants import TVDBSeasonType
from api.schemas.tracked_anime_schemas import (TrackedAnimeCreateRequest, TrackedAnimeRawSettings,
                                               TrackedAnimeTVDBSettings)

_TA = "components.operational_components.tracked_anime_component.TrackedAnimeComponent"
_ANILIST = "components.service_components.anilist_component.AnilistComponent"
_AIRING = ("components.service_components.anilist_airing_schedule_component"
           ".AnilistAiringScheduleComponent")
_MODULE = "components.api_components.tracked_anime_api_component"


def make_request(anilist_id):
    return TrackedAnimeCreateRequest(
        anilist_id=anilist_id, show_parent_directory="/a", show_folder_name="Show", from_episode=1,
        episode_number_padding=2, tvdb_structure_enabled=False, release_profile=None,
        raw_settings=TrackedAnimeRawSettings(raw_episode_file_name_format="{title} {episode}"),
        tvdb_settings=TrackedAnimeTVDBSettings(
            tvdb_season_type=TVDBSeasonType.OFFICIAL, season_number_padding=2,
            season_directory_number_padding=1, season_directory_name_format="S{season}",
            episode_file_name_format="{title} {episode}", titleless_episode_file_name_format="{episode}"),
        release_group_settings=[],
    )


@dataclass
class Case:
    id: str
    anilist_id: int


CASES = [Case(id="returns item with id and all release groups", anilist_id=8501)]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_create_tracked_anime(case: Case, make_anime, make_full_tracked_anime, mocker):
    anime = make_anime(anilist_id=case.anilist_id)
    tracked = make_full_tracked_anime(anilist_id=case.anilist_id)
    mocker.patch(f"{_ANILIST}.get_anime", return_value=anime)
    repo_create = mocker.patch(f"{_TA}.create_tracked_anime", return_value=tracked)
    mocker.patch(f"{_TA}.get_tracked_anime_by_id", return_value=tracked)
    mocker.patch(f"{_AIRING}.get_future_anime_schedule_records_map", return_value={})
    mocker.patch(f"{_MODULE}.anime_relations.get_anilist_id_tvdb_series_id", return_value=None)

    result = await TrackedAnimeAPIComponent().create_tracked_anime(body=make_request(case.anilist_id))

    repo_create.assert_awaited_once()
    assert result.id == tracked.id
    assert result.anilist_id == case.anilist_id
    assert result.user_entry is None
    assert len(result.release_group_settings) == len(config.release_groups_map)
