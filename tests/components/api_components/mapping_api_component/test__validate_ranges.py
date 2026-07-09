from dataclasses import dataclass, field

import pytest

from common.exceptions import ValidationException
from components.api_components.mapping_api_component import MappingAPIComponent
from tests.support.builders import make_mapping_request


@dataclass
class Case:
    id: str
    overrides: dict = field(default_factory=dict)
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="valid 1:1 range"),
    Case(id="valid open-ended (both 'to' null)",
         overrides=dict(anilist_episode_number_to=None, tvdb_episode_number_to=None)),
    Case(id="valid granularity 2 (anilist count == 2x tvdb count)",
         overrides=dict(granularity=2, anilist_episode_number_to=4,
                        tvdb_episode_number_from=1, tvdb_episode_number_to=2)),
    Case(id="valid granularity -2 (tvdb count == 2x anilist count)",
         overrides=dict(granularity=-2, anilist_episode_number_to=2,
                        tvdb_episode_number_from=1, tvdb_episode_number_to=4)),
    Case(id="granularity 0 rejected",
         overrides=dict(granularity=0), expected_exception=ValidationException),
    Case(id="granularity -1 rejected",
         overrides=dict(granularity=-1), expected_exception=ValidationException),
    Case(id="only one 'to' set rejected",
         overrides=dict(tvdb_episode_number_to=None), expected_exception=ValidationException),
    Case(id="anilist from > to rejected",
         overrides=dict(anilist_episode_number_from=5, anilist_episode_number_to=3),
         expected_exception=ValidationException),
    Case(id="tvdb from > to rejected",
         overrides=dict(tvdb_episode_number_from=5, tvdb_episode_number_to=3),
         expected_exception=ValidationException),
    Case(id="granularity 1 unequal counts rejected",
         overrides=dict(tvdb_episode_number_to=2), expected_exception=ValidationException),
    Case(id="granularity 2 wrong multiple rejected",
         overrides=dict(granularity=2, tvdb_episode_number_to=2),
         expected_exception=ValidationException),
    Case(id="granularity -2 wrong multiple rejected",
         overrides=dict(granularity=-2, anilist_episode_number_to=2, tvdb_episode_number_to=3),
         expected_exception=ValidationException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__validate_ranges(case: Case):
    body = make_mapping_request(**case.overrides)

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            MappingAPIComponent._validate_ranges(body)
        return

    assert MappingAPIComponent._validate_ranges(body) is None
