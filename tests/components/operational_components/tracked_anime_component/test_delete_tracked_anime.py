from dataclasses import dataclass

import pytest

from common.exceptions import ObjectNotFoundException
from components.operational_components.tracked_anime_component import TrackedAnimeComponent


@dataclass
class Case:
    id: str
    found: bool
    delete_kwargs: dict
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="delete by anilist id removes record", found=True,
         delete_kwargs={"anilist_ids": [8401]}),
    Case(id="delete missing raises", found=False,
         delete_kwargs={"anilist_ids": [999421]},
         expected_exception=ObjectNotFoundException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_delete_tracked_anime(case: Case, make_tracked_anime, mocker):
    tracked = make_tracked_anime(anilist_id=8401)
    tracked.release_groups_preferences = []
    mocker.patch(
        "repositories.tracked_anime_repositories.tracked_anime_repo.TrackedAnimeRepo.get_tracked_anime_list",
        return_value=[tracked] if case.found else [])
    repo_delete = mocker.patch(
        "repositories.tracked_anime_repositories.tracked_anime_repo.TrackedAnimeRepo.delete_tracked_anime")
    mocker.patch("components.audit_log_component.AuditLogComponent.log_tracked_anime_added_or_removed")

    component = TrackedAnimeComponent()
    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await component.delete_tracked_anime(**case.delete_kwargs)
        repo_delete.assert_not_awaited()
        return

    await component.delete_tracked_anime(**case.delete_kwargs)
    repo_delete.assert_awaited_once_with(tracked_anime_id=tracked.id)
