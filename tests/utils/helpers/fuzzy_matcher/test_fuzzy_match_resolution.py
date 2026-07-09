from dataclasses import dataclass

import pytest

from constants import Resolution
from utils.helpers.fuzzy_matcher import fuzzy_match_resolution


@dataclass
class Case:
    id: str
    text: str
    expected_result: Resolution | None


CASES = [
    Case(id="1080p", text="1080p", expected_result=Resolution.P1080),
    Case(id="1080", text="1080", expected_result=Resolution.P1080),
    Case(id="fhd", text="fhd", expected_result=Resolution.P1080),
    Case(id="full hd", text="full hd", expected_result=Resolution.P1080),
    Case(id="1920x1080", text="1920x1080", expected_result=Resolution.P1080),
    Case(id="720p", text="720p", expected_result=Resolution.P720),
    Case(id="HD", text="HD", expected_result=Resolution.P720),
    Case(id="1280x720", text="1280x720", expected_result=Resolution.P720),
    Case(id="480p", text="480p", expected_result=Resolution.P480),
    Case(id="sd", text="sd", expected_result=Resolution.P480),
    Case(id="540p", text="540p", expected_result=Resolution.P540),
    Case(id="540", text="540", expected_result=Resolution.P540),
    Case(id="960x540", text="960x540", expected_result=Resolution.P540),
    Case(id="empty -> None", text="", expected_result=None),
    Case(id="2160p -> None", text="2160p", expected_result=Resolution.P2160),
    Case(id="1440p -> None", text="1440p", expected_result=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_fuzzy_match_resolution(case: Case):
    assert fuzzy_match_resolution(case.text) == case.expected_result
