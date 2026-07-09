from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from components.operational_components.tracked_anime_component import TrackedAnimeComponent

_REPO = ("repositories.tracked_anime_repositories.tracked_anime_release_group_preferences_repo"
         ".TrackedAnimeReleaseGroupPreferencesRepo")


@dataclass
class Case:
    id: str
    existing: bool


CASES = [
    Case(id="updates the existing preference", existing=True),
    Case(id="creates a preference when none exists", existing=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_tracked_anime_release_group_overriding_title(case: Case, mocker):
    existing = SimpleNamespace(id=77) if case.existing else None
    mocker.patch(f"{_REPO}.get_tracked_anime_release_group_preferences", return_value=existing)
    update = mocker.patch(f"{_REPO}.update_tracked_anime_release_group_preferences")
    create = mocker.patch(f"{_REPO}.create_tracked_anime_release_group_preferences")

    await TrackedAnimeComponent().update_tracked_anime_release_group_overriding_title(
        tracked_anime_id=3, release_group="SubsPlease", title="Naruto S2", offset=12)

    # "S2" suffix is normalized to "Season 2"
    if case.existing:
        update.assert_awaited_once_with(preferences_id=77,
                                        override_match_against="Naruto Season 2", episode_number_offset=12)
        create.assert_not_awaited()
    else:
        create.assert_awaited_once_with(tracked_anime_id=3, release_group="SubsPlease",
                                        override_match_against="Naruto Season 2", episode_number_offset=12)
        update.assert_not_awaited()
