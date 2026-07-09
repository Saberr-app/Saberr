from dataclasses import dataclass

import pytest

from components.operational_components.tracked_anime_component import TrackedAnimeComponent

_REPO = "repositories.tracked_anime_repositories.tracked_anime_repo.TrackedAnimeRepo"


@dataclass
class Case:
    id: str
    anilist_id: int
    load_relations: bool
    found: bool


CASES = [
    Case(id="returns record with relations", anilist_id=8401, load_relations=True, found=True),
    Case(id="passes load_relations through", anilist_id=8402, load_relations=False, found=True),
    Case(id="returns none when missing", anilist_id=8403, load_relations=True, found=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_tracked_anime(case: Case, make_tracked_anime, mocker):
    tracked = make_tracked_anime(anilist_id=case.anilist_id) if case.found else None
    repo_get = mocker.patch(f"{_REPO}.get_tracked_anime", return_value=tracked)

    result = await TrackedAnimeComponent().get_tracked_anime(anilist_id=case.anilist_id,
                                                             load_relations=case.load_relations)

    assert result is tracked
    repo_get.assert_awaited_once_with(anilist_id=case.anilist_id, load_relations=case.load_relations)
