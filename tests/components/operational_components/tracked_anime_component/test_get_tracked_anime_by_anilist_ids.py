from dataclasses import dataclass

import pytest

from components.operational_components.tracked_anime_component import TrackedAnimeComponent

_REPO = "repositories.tracked_anime_repositories.tracked_anime_repo.TrackedAnimeRepo"


@dataclass
class Case:
    id: str
    anilist_ids: list[int]
    load_relations: bool


CASES = [
    Case(id="forwards ids and relations", anilist_ids=[8601, 8602], load_relations=True),
    Case(id="passes load_relations through", anilist_ids=[8603], load_relations=False),
    Case(id="empty id list", anilist_ids=[], load_relations=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_tracked_anime_by_anilist_ids(case: Case, make_tracked_anime, mocker):
    tracked = [make_tracked_anime(anilist_id=anilist_id) for anilist_id in case.anilist_ids]
    repo_get = mocker.patch(f"{_REPO}.get_tracked_anime_list", return_value=tracked)

    result = await TrackedAnimeComponent().get_tracked_anime_by_anilist_ids(
        anilist_ids=case.anilist_ids, load_relations=case.load_relations)

    assert result == tracked
    repo_get.assert_awaited_once_with(anilist_ids=case.anilist_ids, load_relations=case.load_relations)
