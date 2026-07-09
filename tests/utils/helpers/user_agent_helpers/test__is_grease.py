from dataclasses import dataclass

import pytest

from utils.helpers.user_agent_helpers import _is_grease


@dataclass
class Case:
    id: str
    brand: str
    expected_result: bool


CASES = [
    Case(id="dotted grease brand", brand="Not.A/Brand", expected_result=True),
    Case(id="punctuated grease brand", brand="Not(A:Brand", expected_result=True),
    Case(id="real chromium brand", brand="Chromium", expected_result=False),
    Case(id="real chrome brand", brand="Google Chrome", expected_result=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__is_grease(case: Case):
    assert _is_grease(case.brand) == case.expected_result
