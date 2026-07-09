from dataclasses import dataclass

import pytest

from utils.helpers.fuzzy_matcher import _extract_episode


@dataclass
class Case:
    id: str
    segment: str
    expected_season: int | None
    expected_episode: int | None


CASES = [
    Case(id="SxxExx yields season and episode", segment="Show S01E08 1080p",
         expected_season=1, expected_episode=8),
    Case(id="Sx - nn yields only episode", segment="Show S7 - 05", expected_season=None, expected_episode=5),
    Case(id="Episode keyword", segment="Show - Episode 48", expected_season=None, expected_episode=48),
    Case(id="dash delimited number", segment="Show - 11 ", expected_season=None, expected_episode=11),
    Case(id="no episode pattern", segment="Show Season 2", expected_season=None, expected_episode=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__extract_episode(case: Case):
    season, episode, _boundary = _extract_episode(case.segment)
    assert season == case.expected_season
    assert episode == case.expected_episode
