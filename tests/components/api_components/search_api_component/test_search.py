from dataclasses import dataclass, field

import pytest

from components.api_components.search_api_component import SearchAPIComponent
from api.schemas.search_schema import SearchRequest
from dto.anilist import AnilistAnime
from tests.support.builders import make_anime

_REPO = "repositories.cache_repositories.anilist_anime_repo.AnilistAnimeRepo"
_ANILIST = "components.service_components.anilist_component.AnilistComponent"
_LIST = "components.service_components.anilist_list_component.AnilistListComponent"
_TA = "components.operational_components.tracked_anime_component.TrackedAnimeComponent"


@dataclass
class Case:
    id: str
    query: str
    cache_results: list[AnilistAnime] = field(default_factory=list)
    anilist_results: list[AnilistAnime] = field(default_factory=list)
    expected_anilist_ids: list[int] = field(default_factory=list)
    repo_awaited: bool = True


CASES = [
    Case(id="query too short returns empty without hitting cache",
         query="ab", expected_anilist_ids=[], repo_awaited=False),
    Case(id="cache miss falls back to anilist and maps results",
         query="naruto", cache_results=[], anilist_results=[make_anime(1, title="Naruto")],
         expected_anilist_ids=[1], repo_awaited=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_search(case: Case, mocker):
    repo = mocker.patch(f"{_REPO}.search_anime", return_value=case.cache_results)
    mocker.patch(f"{_ANILIST}.get_anime_with_filters", return_value=case.anilist_results)
    mocker.patch(f"{_TA}.get_tracked_anime_by_anilist_ids", return_value=[])
    mocker.patch(f"{_LIST}.get_user_anime_list_entries", return_value=[])

    result = await SearchAPIComponent().search(body=SearchRequest(query=case.query))

    assert [item.anilist_id for item in result.anime] == case.expected_anilist_ids
    if case.repo_awaited:
        repo.assert_awaited()
    else:
        repo.assert_not_awaited()  # too short to even hit the cache
    if case.expected_anilist_ids:
        assert result.anime[0].tracked_anime_id is None
        assert result.anime[0].user_list_status is None
