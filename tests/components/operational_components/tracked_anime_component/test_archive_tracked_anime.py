from dataclasses import dataclass

import pytest

from common.exceptions import ObjectNotFoundException
from components.operational_components.tracked_anime_component import TrackedAnimeComponent
from constants import TrackedAnimeStatus


@dataclass
class Case:
    id: str
    found: bool
    archive_kwargs: dict
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="archive by anilist id updates status to archived", found=True,
         archive_kwargs={"anilist_ids": [8301]}),
    Case(id="archive missing raises", found=False,
         archive_kwargs={"tracked_anime_ids": [999321]},
         expected_exception=ObjectNotFoundException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_archive_tracked_anime(case: Case, make_tracked_anime, mocker):
    tracked = make_tracked_anime(anilist_id=8301)
    mocker.patch(
        "repositories.tracked_anime_repositories.tracked_anime_repo.TrackedAnimeRepo.get_tracked_anime_list",
        return_value=[tracked] if case.found else [])
    repo_update = mocker.patch(
        "repositories.tracked_anime_repositories.tracked_anime_repo.TrackedAnimeRepo.update_tracked_anime")
    mocker.patch("components.audit_log_component.AuditLogComponent.log_tracked_anime_archived")

    component = TrackedAnimeComponent()
    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await component.archive_tracked_anime(**case.archive_kwargs)
        repo_update.assert_not_awaited()
        return

    await component.archive_tracked_anime(**case.archive_kwargs)
    repo_update.assert_awaited_once_with(tracked_anime_id=tracked.id, status=TrackedAnimeStatus.ARCHIVED)
