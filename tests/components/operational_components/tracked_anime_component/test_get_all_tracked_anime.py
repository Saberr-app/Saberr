from dataclasses import dataclass

import pytest

from components.operational_components.tracked_anime_component import TrackedAnimeComponent
from constants import TrackedAnimeStatus

_REPO = "repositories.tracked_anime_repositories.tracked_anime_repo.TrackedAnimeRepo"


@dataclass
class Case:
    id: str
    statuses: list[TrackedAnimeStatus] | None
    expected_statuses: list[TrackedAnimeStatus]


CASES = [
    Case(id="forwards explicit statuses",
         statuses=[TrackedAnimeStatus.ACTIVE],
         expected_statuses=[TrackedAnimeStatus.ACTIVE]),
    Case(id="none defaults to active",
         statuses=None,
         expected_statuses=[TrackedAnimeStatus.ACTIVE]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_all_tracked_anime(case: Case, make_tracked_anime, mocker):
    tracked = [make_tracked_anime(anilist_id=8501), make_tracked_anime(anilist_id=8502)]
    repo_get = mocker.patch(f"{_REPO}.get_all_tracked_anime", return_value=tracked)

    result = await TrackedAnimeComponent().get_all_tracked_anime(statuses=case.statuses)

    assert result == tracked
    repo_get.assert_awaited_once_with(statuses=case.expected_statuses, load_relations=True, anilist_ids=None)
