from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from components.operational_components.tracked_anime_profile_component import TrackedAnimeProfileComponent

_REPO = "repositories.tracked_anime_repositories.tracked_anime_profile_repo.TrackedAnimeProfileRepo"


@dataclass
class Case:
    id: str
    expected_profile_id: int = 1


CASES = [
    Case(id="reads the default profile (id=1)"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_default_tracked_anime_profile(case: Case, mocker):
    profile = MagicMock()
    repo_get = mocker.patch(f"{_REPO}.get_tracked_anime_profile", return_value=profile)

    result = await TrackedAnimeProfileComponent().get_default_tracked_anime_profile()

    assert result is profile
    assert repo_get.await_args.kwargs["tracked_anime_profile_id"] == case.expected_profile_id
