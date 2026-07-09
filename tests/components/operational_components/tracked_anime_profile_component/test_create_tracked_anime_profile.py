from dataclasses import dataclass, field
from unittest.mock import MagicMock

import pytest

from constants import Encoding, Resolution, VideoSource, ReleaseCriteriaProperty
from components.operational_components.tracked_anime_profile_component import TrackedAnimeProfileComponent

_REPO = "repositories.tracked_anime_repositories.tracked_anime_profile_repo.TrackedAnimeProfileRepo"


def _kwargs():
    return dict(
        preferred_release_groups=["GroupA", "GroupB"],
        preferred_encodings=[Encoding.HEVC],
        preferred_resolutions=[Resolution.P1080],
        preferred_language_codes=["eng"],
        preferred_sources=[VideoSource.CRUNCHYROLL],
        language_codes_restricted=True,
        sources_restricted=False,
        accept_release_upgrades=True,
        priorities_sorted=[ReleaseCriteriaProperty.RESOLUTION, ReleaseCriteriaProperty.RELEASE_GROUP],
    )


@dataclass
class Case:
    id: str
    kwargs: dict = field(default_factory=_kwargs)


CASES = [
    Case(id="forwards every argument to the repo verbatim"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_create_tracked_anime_profile(case: Case, mocker):
    created = MagicMock()
    repo_create = mocker.patch(f"{_REPO}.create_tracked_anime_profile", return_value=created)

    result = await TrackedAnimeProfileComponent().create_tracked_anime_profile(**case.kwargs)

    assert result is created
    assert repo_create.await_args.kwargs == case.kwargs
