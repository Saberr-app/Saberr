from dataclasses import dataclass

import pytest

from components.operational_components.tracked_anime_component import TrackedAnimeComponent

_REPO = "repositories.tracked_anime_repositories.tracked_anime_repo.TrackedAnimeRepo"


@dataclass
class Case:
    id: str
    tracked_anime_id: int
    load_relations: bool
    found: bool


CASES = [
    Case(id="returns record with relations", tracked_anime_id=11, load_relations=True, found=True),
    Case(id="passes load_relations through", tracked_anime_id=12, load_relations=False, found=True),
    Case(id="returns none when missing", tracked_anime_id=13, load_relations=True, found=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_tracked_anime_by_id(case: Case, make_tracked_anime, mocker):
    tracked = make_tracked_anime(anilist_id=1) if case.found else None
    repo_get = mocker.patch(f"{_REPO}.get_tracked_anime", return_value=tracked)

    result = await TrackedAnimeComponent().get_tracked_anime_by_id(
        tracked_anime_id=case.tracked_anime_id, load_relations=case.load_relations)

    assert result is tracked
    repo_get.assert_awaited_once_with(tracked_anime_id=case.tracked_anime_id,
                                      load_relations=case.load_relations)
