from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from components.operational_components.tracked_anime_component import TrackedAnimeComponent

_TA_REPO = "repositories.tracked_anime_repositories.tracked_anime_repo.TrackedAnimeRepo"
_PROC_REPO = ("repositories.tracked_anime_repositories.tracked_anime_processing_settings_repo"
              ".TrackedAnimeProcessingSettingsRepo")
_RGP_REPO = ("repositories.tracked_anime_repositories.tracked_anime_release_group_preferences_repo"
             ".TrackedAnimeReleaseGroupPreferencesRepo")
_PROFILE_COMPONENT = ("components.operational_components.tracked_anime_profile_component"
                      ".TrackedAnimeProfileComponent")


@dataclass
class Case:
    id: str
    anilist_id: int
    use_profile_settings: bool
    expected_profile_id: int
    extra_kwargs: dict = field(default_factory=dict)


# a release-group-preference row is created for each release group named in the overriding-title map
_OVERRIDE_TITLES = {"GroupA": "AltA", "GroupB": None}
_OVERRIDE_OFFSETS = {"GroupA": 2}


CASES = [
    Case(id="uses default profile (id=1) when release_profile is None", anilist_id=8101,
         use_profile_settings=False, expected_profile_id=1),
    Case(id="makes dedicated profile with enabled groups", anilist_id=8102,
         use_profile_settings=True, expected_profile_id=99),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_create_tracked_anime(case: Case, make_anime, base_kwargs, make_tracked_anime,
                                    profile_settings, mocker):
    repo_create = mocker.patch(f"{_TA_REPO}.create_tracked_anime",
                               return_value=make_tracked_anime(anilist_id=case.anilist_id))
    proc_create = mocker.patch(f"{_PROC_REPO}.create_tracked_anime_processing_settings")
    rgp_create = mocker.patch(f"{_RGP_REPO}.create_tracked_anime_release_group_preferences",
                              return_value=MagicMock())
    mocker.patch(f"{_PROFILE_COMPONENT}.create_tracked_anime_profile",
                 return_value=SimpleNamespace(id=99))
    mocker.patch(f"{_PROFILE_COMPONENT}.get_default_tracked_anime_profile",
                 return_value=SimpleNamespace(id=1))
    mocker.patch("components.audit_log_component.AuditLogComponent.log_tracked_anime_added_or_removed")

    kwargs = dict(case.extra_kwargs)
    kwargs.update(release_group_overriding_title_map=_OVERRIDE_TITLES,
                  release_group_overriding_offset_map=_OVERRIDE_OFFSETS)
    if case.use_profile_settings:
        kwargs.update(release_profile=profile_settings)

    result = await TrackedAnimeComponent().create_tracked_anime(**base_kwargs(
        make_anime(anilist_id=case.anilist_id), **kwargs))

    assert result is repo_create.return_value
    passed = repo_create.await_args.kwargs
    assert passed["tracked_anime_profile_id"] == case.expected_profile_id
    assert passed["romaji_title"] == "Romaji"
    assert passed["anilist_id"] == case.anilist_id
    proc_create.assert_awaited_once()
    # one release-group-preference row per release group named in the overriding-title map
    assert rgp_create.await_count == len(_OVERRIDE_TITLES)
