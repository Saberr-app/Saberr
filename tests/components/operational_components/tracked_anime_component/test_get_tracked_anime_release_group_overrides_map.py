from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from components.operational_components.tracked_anime_component import TrackedAnimeComponent

_REPO = "repositories.tracked_anime_repositories.tracked_anime_repo.TrackedAnimeRepo"


def _pref(override_match_against, release_group):
    return SimpleNamespace(override_match_against=override_match_against, release_group=release_group)


@dataclass
class Case:
    id: str
    preferences: list = field(default_factory=list)
    expected_keys: list[tuple[str, str]] = field(default_factory=list)


CASES = [
    Case(id="empty preferences yields an empty map"),
    Case(id="maps each preference by (overriding title, release group)",
         preferences=[_pref("Title A", "SubsPlease"), _pref("Title B", "Erai-raws")],
         expected_keys=[("Title A", "SubsPlease"), ("Title B", "Erai-raws")]),
    Case(id="first preference wins on a duplicate key",
         preferences=[_pref("Title A", "SubsPlease"), _pref("Title A", "SubsPlease")],
         expected_keys=[("Title A", "SubsPlease")]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_tracked_anime_release_group_overrides_map(case: Case, mocker):
    pairs = {(pref.override_match_against, pref.release_group) for pref in case.preferences}
    repo_get = mocker.patch(f"{_REPO}.get_release_group_preferences_for_overriding_titles",
                            return_value=case.preferences)

    result = await TrackedAnimeComponent().get_tracked_anime_release_group_overrides_map(
        title_release_group_pairs=pairs)

    assert set(result.keys()) == set(case.expected_keys)
    first_by_key = {}
    for pref in case.preferences:
        first_by_key.setdefault((pref.override_match_against, pref.release_group), pref)
    for key, pref in first_by_key.items():
        assert result[key] is pref  # first preference wins per key
    repo_get.assert_awaited_once_with(title_release_group_pairs=pairs)
