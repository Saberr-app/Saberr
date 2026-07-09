from dataclasses import dataclass

import pytest

from components.operational_components.tracked_anime_component import TrackedAnimeComponent


@dataclass
class Case:
    id: str
    title: str | None
    expected_result: str | None


CASES = [
    Case(id="trailing Sx expands to Season x", title="Show S2", expected_result="Show Season 2"),
    Case(id="zero-padded Sxx expands and drops padding", title="Show S02", expected_result="Show Season 2"),
    Case(id="no season suffix is unchanged", title="Show", expected_result="Show"),
    Case(id="already expanded season is unchanged", title="Show Season 3", expected_result="Show Season 3"),
    Case(id="season marker not at the end is unchanged", title="Show S2 extra", expected_result="Show S2 extra"),
    Case(id="none stays none", title=None, expected_result=None),
    Case(id="empty becomes none", title="", expected_result=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__normalize_overriding_title(case: Case):
    assert TrackedAnimeComponent._normalize_overriding_title(case.title) == case.expected_result
