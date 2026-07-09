from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from constants import Encoding, Resolution, VideoSource, ReleaseCriteriaProperty
from api.schemas.settings_schemas import ProfileSettings

_PROFILE_COMPONENT = ("components.operational_components.tracked_anime_profile_component"
                      ".TrackedAnimeProfileComponent")


@dataclass
class Case:
    id: str
    body: ProfileSettings


CASES = [
    Case(id="persists and returns profile section",
         body=ProfileSettings(
             preferred_release_groups=["SubsPlease"],
             preferred_encodings=[Encoding.AV1],
             preferred_resolutions=[Resolution.P720],
             preferred_language_codes=["EN"],
             preferred_sources=[VideoSource.CRUNCHYROLL],
             language_codes_restricted=True,
             sources_restricted=True,
             accept_release_upgrades=False,
             priorities_sorted=[ReleaseCriteriaProperty.ENCODING, ReleaseCriteriaProperty.RESOLUTION],
         )),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_profile_settings(case: Case, settings_api, mocker):
    repo_update = mocker.patch(f"{_PROFILE_COMPONENT}.update_tracked_anime_profile")
    # get_default returns the persisted profile (mirrors the body that was just written)
    updated_profile = SimpleNamespace(id=1, **case.body.model_dump())
    mocker.patch(f"{_PROFILE_COMPONENT}.get_default_tracked_anime_profile", return_value=updated_profile)

    result = await settings_api.update_profile_settings(case.body)

    # default profile (id=1) updated with the body's fields
    repo_update.assert_awaited_once_with(
        profile_id=1,
        preferred_release_groups=case.body.preferred_release_groups,
        preferred_encodings=case.body.preferred_encodings,
        preferred_resolutions=case.body.preferred_resolutions,
        preferred_language_codes=case.body.preferred_language_codes,
        preferred_sources=case.body.preferred_sources,
        language_codes_restricted=case.body.language_codes_restricted,
        sources_restricted=case.body.sources_restricted,
        accept_release_upgrades=case.body.accept_release_upgrades,
        priorities_sorted=case.body.priorities_sorted,
    )
    assert result.preferred_release_groups == ["SubsPlease"]
    assert [e.value for e in result.preferred_encodings] == ["AV1"]
    assert result.priorities_sorted == [ReleaseCriteriaProperty.ENCODING, ReleaseCriteriaProperty.RESOLUTION]
