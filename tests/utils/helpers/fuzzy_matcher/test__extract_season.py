from dataclasses import dataclass

import pytest

from utils.helpers.fuzzy_matcher import _extract_season


@dataclass
class Case:
    id: str
    segment: str
    expected_season: int | None


CASES = [
    Case(id="Season word form", segment="Show Season 2 stuff", expected_season=2),
    Case(id="Sxx form", segment="Show S03 stuff", expected_season=3),
    Case(id="episode marker is not a season", segment="Show E05", expected_season=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__extract_season(case: Case):
    season, _boundary = _extract_season(case.segment)
    assert season == case.expected_season
