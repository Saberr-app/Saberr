from dataclasses import dataclass

import pytest

from utils.helpers.fuzzy_matcher import _detect_language


@dataclass
class Case:
    id: str
    tech_region: str
    expected_result: str | None


CASES = [
    Case(id="dual audio", tech_region="Dual Audio 1080p", expected_result="dual"),
    Case(id="multi audio", tech_region="Multi-Audio", expected_result="multi"),
    Case(id="two named audio languages collapse to multi", tech_region="English Japanese",
         expected_result="multi"),
    Case(id="no language markers", tech_region="1080p HEVC", expected_result=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__detect_language(case: Case):
    assert _detect_language(case.tech_region) == case.expected_result
