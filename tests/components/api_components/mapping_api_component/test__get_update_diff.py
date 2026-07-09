from dataclasses import dataclass, field

import pytest

from constants import MappingOverrideMode
from components.api_components.mapping_api_component import MappingAPIComponent
from tests.support.builders import make_mapping_override, make_mapping_request


@dataclass
class Case:
    id: str
    body_overrides: dict = field(default_factory=dict)
    expected_update_data: dict = field(default_factory=dict)
    expected_updated_data: dict = field(default_factory=dict)


CASES = [
    Case(id="no changes -> empty diff"),
    Case(id="anilist_id changed",
         body_overrides=dict(anilist_id=999),
         expected_update_data={"anilist_id": 999},
         expected_updated_data={"AniList ID": {"old": 100, "new": 999}}),
    Case(id="tvdb_season_number changed",
         body_overrides=dict(tvdb_season_number=2),
         expected_update_data={"tvdb_season_number": 2},
         expected_updated_data={"TVDB season number": {"old": 1, "new": 2}}),
    Case(id="mode changed -> human-readable old/new",
         body_overrides=dict(mode=MappingOverrideMode.IF_MISSING),
         expected_update_data={"mode": MappingOverrideMode.IF_MISSING},
         expected_updated_data={"Mode": {"old": "Always", "new": "If missing"}}),
    Case(id="multiple fields changed",
         body_overrides=dict(anilist_episode_number_from=2, granularity=1, tvdb_episode_number_from=2),
         expected_update_data={"anilist_episode_number_from": 2, "tvdb_episode_number_from": 2},
         expected_updated_data={"AniList episode 'from'": {"old": 1, "new": 2},
                                "TVDB episode 'from'": {"old": 1, "new": 2}}),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__get_update_diff(case: Case):
    override = make_mapping_override()
    body = make_mapping_request(**case.body_overrides)

    update_data, updated_data = MappingAPIComponent._get_update_diff(override, body)

    assert update_data == case.expected_update_data
    assert updated_data == case.expected_updated_data
