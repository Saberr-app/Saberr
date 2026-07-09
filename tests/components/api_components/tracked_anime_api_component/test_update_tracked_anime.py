from dataclasses import dataclass

import pytest

from common.exceptions import NotFoundException
from components.api_components.tracked_anime_api_component import TrackedAnimeAPIComponent
from constants import TVDBSeasonType
from api.schemas.tracked_anime_schemas import (TrackedAnimeUpdateRequest, TrackedAnimeRawSettings,
                                               TrackedAnimeTVDBSettings, TrackedAnimeReleaseGroupSettings)

_TA = "components.operational_components.tracked_anime_component.TrackedAnimeComponent"
_ANILIST = "components.service_components.anilist_component.AnilistComponent"
_AIRING = ("components.service_components.anilist_airing_schedule_component"
           ".AnilistAiringScheduleComponent")
_MODULE = "components.api_components.tracked_anime_api_component"


def make_update():
    return TrackedAnimeUpdateRequest(
        show_parent_directory="/new", show_folder_name="New", episode_number_padding=3, from_episode=2,
        tvdb_structure_enabled=True, release_profile=None,
        raw_settings=TrackedAnimeRawSettings(raw_episode_file_name_format="{episode}"),
        tvdb_settings=TrackedAnimeTVDBSettings(
            tvdb_season_type=TVDBSeasonType.OFFICIAL, season_number_padding=2,
            season_directory_number_padding=1, season_directory_name_format="S{season}",
            episode_file_name_format="{title} {episode}", titleless_episode_file_name_format="{episode}"),
        release_group_settings=[
            TrackedAnimeReleaseGroupSettings(release_group_name="GroupA",
                                             episode_number_offset=2, override_match_against="AltA"),
            TrackedAnimeReleaseGroupSettings(release_group_name="GroupB",
                                             episode_number_offset=0, override_match_against=None),
        ],
    )


@dataclass
class Case:
    id: str
    flow: str  # "happy" | "tracked_missing" | "anime_missing"


CASES = [
    Case(id="forwards settings and returns mapped item", flow="happy"),
    Case(id="missing tracked anime maps to NotFoundException", flow="tracked_missing"),
    Case(id="missing anilist anime maps to NotFoundException", flow="anime_missing"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_tracked_anime(case: Case, make_anime, make_full_tracked_anime, mocker):
    component = TrackedAnimeAPIComponent()
    tracked = make_full_tracked_anime(anilist_id=8711, show_folder_name="New",
                                      episode_number_padding=3, tvdb_structure_enabled=True)
    anime = make_anime(anilist_id=8711)
    body = make_update()

    op_update = mocker.patch(f"{_TA}.update_tracked_anime")
    mocker.patch(f"{_TA}.get_tracked_anime_by_id",
                 return_value=None if case.flow == "tracked_missing" else tracked)
    mocker.patch(f"{_ANILIST}.get_anime",
                 return_value=None if case.flow == "anime_missing" else anime)
    mocker.patch(f"{_AIRING}.get_future_anime_schedule_records_map", return_value={})
    mocker.patch(f"{_MODULE}.anime_relations.get_anilist_id_tvdb_series_id", return_value=None)

    if case.flow != "happy":
        with pytest.raises(NotFoundException):
            await component.update_tracked_anime(tracked_anime_id=tracked.id, body=body)
        return

    result = await component.update_tracked_anime(tracked_anime_id=tracked.id, body=body)

    op_update.assert_awaited_once()
    kwargs = op_update.await_args.kwargs
    assert kwargs["tracked_anime_id"] == tracked.id
    assert kwargs["from_episode"] == 2
    assert kwargs["release_group_overriding_offset_map"] == {"GroupA": 2, "GroupB": 0}
    assert kwargs["release_group_overriding_title_map"] == {"GroupA": "AltA", "GroupB": None}
    assert result.id == tracked.id
    assert result.show_folder_name == "New"
    assert result.episode_number_padding == 3
    assert result.tvdb_structure_enabled is True
