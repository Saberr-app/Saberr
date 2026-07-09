from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from components.operational_components.tracked_anime_component import TrackedAnimeComponent

_TA_REPO = "repositories.tracked_anime_repositories.tracked_anime_repo.TrackedAnimeRepo"
_PROFILE_REPO = ("repositories.tracked_anime_repositories.tracked_anime_profile_repo"
                 ".TrackedAnimeProfileRepo")
_PROFILE_COMPONENT = ("components.operational_components.tracked_anime_profile_component"
                      ".TrackedAnimeProfileComponent")


@dataclass
class Case:
    id: str
    current_profile_id: int
    new_profile: object  # release_profile arg
    expected_new_profile_id: int
    expect_delete_of: int | None


CASES = [
    Case(id="assigning a profile on default creates a dedicated one", current_profile_id=1,
         new_profile=object(), expected_new_profile_id=99, expect_delete_of=None),
    Case(id="clearing the profile relinks to default and deletes the orphan", current_profile_id=77,
         new_profile=None, expected_new_profile_id=1, expect_delete_of=77),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_tracked_anime(case: Case, make_tracked_anime, profile_settings, mocker):
    tracked = make_tracked_anime(anilist_id=8201)
    tracked.tracked_anime_profile_id = case.current_profile_id
    tracked.release_groups_preferences = []

    mocker.patch(f"{_TA_REPO}.get_tracked_anime", return_value=tracked)
    repo_update = mocker.patch(f"{_TA_REPO}.update_tracked_anime")
    profile_delete = mocker.patch(f"{_PROFILE_REPO}.delete_tracked_anime_profile")
    mocker.patch(f"{_PROFILE_COMPONENT}.create_tracked_anime_profile",
                 return_value=SimpleNamespace(id=99))

    release_profile = profile_settings if case.new_profile is not None else None
    await TrackedAnimeComponent().update_tracked_anime(tracked_anime_id=tracked.id,
                                                       release_profile=release_profile)

    repo_update.assert_awaited_once_with(tracked_anime_id=tracked.id,
                                         tracked_anime_profile_id=case.expected_new_profile_id)
    if case.expect_delete_of is not None:
        profile_delete.assert_awaited_once_with(profile_id=case.expect_delete_of)
    else:
        profile_delete.assert_not_awaited()
