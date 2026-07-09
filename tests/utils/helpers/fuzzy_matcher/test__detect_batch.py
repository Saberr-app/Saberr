from dataclasses import dataclass

import pytest

from utils.helpers.fuzzy_matcher import _detect_batch


@dataclass
class Case:
    id: str
    text: str
    episode_number: int | None
    expected_result: bool


CASES = [
    Case(id="complete keyword", text="Show Complete", episode_number=None, expected_result=True),
    Case(id="episode range", text="Show 01-12", episode_number=None, expected_result=True),
    Case(id="season without an episode is a batch", text="Show Season 2", episode_number=None,
         expected_result=True),
    Case(id="season with an episode is not a batch", text="Show Season 2", episode_number=5,
         expected_result=False),
    Case(id="plain single release", text="Show 1080p HEVC", episode_number=5, expected_result=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__detect_batch(case: Case):
    assert _detect_batch(case.text, case.episode_number) == case.expected_result
