from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from common.exceptions import ObjectNotFoundException
from constants import Encoding, Resolution, ReleaseCriteriaProperty
from components.operational_components.tracked_anime_profile_component import TrackedAnimeProfileComponent

_REPO = "repositories.tracked_anime_repositories.tracked_anime_profile_repo.TrackedAnimeProfileRepo"
_AUDIT = "components.audit_log_component.AuditLogComponent"

_TRACKED_ANIME = SimpleNamespace(id=55)


@dataclass
class Case:
    id: str
    profile_id: int = 1
    profile_found: bool = True
    profile_kwargs: dict = field(default_factory=dict)   # stored profile state (make_profile overrides)
    update_kwargs: dict = field(default_factory=dict)    # args passed to update_tracked_anime_profile
    expected_exception: type[Exception] | None = None
    expected_update_called: bool = True
    expected_update_subset: dict = field(default_factory=dict)
    expected_update_keys: set | None = None   # exact set of kwargs forwarded to the repo (incl. profile_id)
    expected_setting_log_count: int = 0
    expected_setting_names: set | None = None
    expected_tracked_log: bool = False
    expected_tracked_update_data: dict | None = None


CASES = [
    Case(id="missing profile raises ObjectNotFoundException",
         profile_id=7, profile_found=False, update_kwargs=dict(accept_release_upgrades=False),
         expected_exception=ObjectNotFoundException, expected_update_called=False),
    Case(id="no changes skips update and audit",
         profile_kwargs=dict(accept_release_upgrades=True),
         update_kwargs=dict(accept_release_upgrades=True), expected_update_called=False),
    Case(id="unset fields are ignored",
         profile_kwargs=dict(accept_release_upgrades=True),
         update_kwargs=dict(accept_release_upgrades=False),
         expected_update_subset=dict(accept_release_upgrades=False),
         expected_update_keys={"profile_id", "accept_release_upgrades"},
         expected_setting_log_count=1),
    Case(id="default profile logs each changed setting",
         profile_id=1,
         profile_kwargs=dict(preferred_release_groups=["GroupA"], preferred_encodings=[Encoding.HEVC],
                             sources_restricted=False),
         update_kwargs=dict(preferred_release_groups=["GroupB"], preferred_encodings=[Encoding.AVC],
                            sources_restricted=True),
         expected_update_subset=dict(preferred_release_groups=["GroupB"], preferred_encodings=[Encoding.AVC],
                                     sources_restricted=True),
         expected_setting_log_count=3,
         expected_setting_names={"Default preferred release groups", "Default preferred encodings",
                                 "Default sources restricted"}),
    Case(id="non-default profile logs a grouped tracked-anime change",
         profile_id=2,
         profile_kwargs=dict(preferred_resolutions=[Resolution.P1080], tracked_anime_list=[_TRACKED_ANIME]),
         update_kwargs=dict(preferred_resolutions=[Resolution.P720]),
         expected_update_subset=dict(preferred_resolutions=[Resolution.P720]),
         expected_tracked_log=True,
         expected_tracked_update_data={"Preferred resolutions": {"old": [Resolution.P1080.value],
                                                                 "new": [Resolution.P720.value]}}),
    Case(id="non-default profile without tracked anime skips audit",
         profile_id=3,
         profile_kwargs=dict(priorities_sorted=[ReleaseCriteriaProperty.RESOLUTION], tracked_anime_list=[]),
         update_kwargs=dict(priorities_sorted=[ReleaseCriteriaProperty.SOURCE, ReleaseCriteriaProperty.VERSION])),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_tracked_anime_profile(case: Case, make_profile, mocker):
    profile = make_profile(**case.profile_kwargs) if case.profile_found else None
    mocker.patch(f"{_REPO}.get_tracked_anime_profile", return_value=profile)
    repo_update = mocker.patch(f"{_REPO}.update_tracked_anime_profile")
    log_setting = mocker.patch(f"{_AUDIT}.log_setting_changed")
    log_tracked = mocker.patch(f"{_AUDIT}.log_tracked_anime_settings_change")

    component = TrackedAnimeProfileComponent()

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await component.update_tracked_anime_profile(profile_id=case.profile_id, **case.update_kwargs)
        repo_update.assert_not_awaited()
        return

    await component.update_tracked_anime_profile(profile_id=case.profile_id, **case.update_kwargs)

    if not case.expected_update_called:
        repo_update.assert_not_awaited()
        log_setting.assert_not_awaited()
        log_tracked.assert_not_awaited()
        return

    repo_update.assert_awaited_once()
    passed = repo_update.await_args.kwargs
    for key, value in case.expected_update_subset.items():
        assert passed[key] == value
    if case.expected_update_keys is not None:
        assert set(passed) == case.expected_update_keys

    assert log_setting.await_count == case.expected_setting_log_count
    if case.expected_setting_names is not None:
        assert {call.kwargs["setting_name"] for call in log_setting.await_args_list} == case.expected_setting_names

    if case.expected_tracked_log:
        log_tracked.assert_awaited_once()
        assert log_tracked.await_args.kwargs["tracked_anime"] is _TRACKED_ANIME
        if case.expected_tracked_update_data is not None:
            assert log_tracked.await_args.kwargs["update_data"] == case.expected_tracked_update_data
    else:
        log_tracked.assert_not_awaited()
