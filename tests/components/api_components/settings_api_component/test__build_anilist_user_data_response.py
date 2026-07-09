from dataclasses import dataclass

import pytest

from api.schemas.settings_schemas import AnilistUserData
from components.api_components.settings_api_component import SettingsAPIComponent
from config import config
from constants import AnilistScoreFormat

_FULL = {
    "name": "Alice",
    "avatar": {"medium": "http://img/av.png"},
    "bannerImage": "http://img/banner.png",
    "statistics": {"anime": {"statuses": [{"status": "CURRENT", "count": 3},
                                          {"status": "COMPLETED", "count": 10}],
                             "meanScore": 78.4}},
    "siteUrl": "http://anilist.co/user/Alice",
    "moderatorRoles": ["ANIME"],
    "mediaListOptions": {"scoreFormat": "POINT_10"},
}

_MINIMAL = {
    "name": "Bob",
    "statistics": {"anime": {"statuses": [], "meanScore": 0}},
    "siteUrl": "http://x",
    "mediaListOptions": {"scoreFormat": "POINT_100"},
}


@dataclass
class Case:
    id: str
    data: dict | None
    expected_result: AnilistUserData | None


CASES = [
    Case(id="empty dict maps to None", data={}, expected_result=None),
    Case(id="None maps to None", data=None, expected_result=None),
    # mean score is rounded; missing statuses default to 0
    Case(id="full payload is mapped",
         data=_FULL,
         expected_result=AnilistUserData(
             username="Alice", avatar="http://img/av.png", banner="http://img/banner.png",
             current_anime_count=3, planning_anime_count=0, completed_anime_count=10,
             mean_score=78.0, site_url="http://anilist.co/user/Alice", moderator_roles=["ANIME"],
             score_format=AnilistScoreFormat.POINT_10)),
    # absent avatar/banner/moderatorRoles and empty statuses fall back to None / 0
    Case(id="minimal payload falls back to None and zero",
         data=_MINIMAL,
         expected_result=AnilistUserData(
             username="Bob", avatar=None, banner=None,
             current_anime_count=0, planning_anime_count=0, completed_anime_count=0,
             mean_score=0.0, site_url="http://x", moderator_roles=None,
             score_format=AnilistScoreFormat.POINT_100)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__build_anilist_user_data_response(case: Case, mocker):
    # keep external image URLs verbatim rather than rewriting them to the proxy endpoint
    mocker.patch.object(config, "proxy_external_images", False)
    assert SettingsAPIComponent._build_anilist_user_data_response(case.data) == case.expected_result
