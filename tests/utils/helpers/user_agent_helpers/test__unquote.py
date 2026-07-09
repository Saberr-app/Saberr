from dataclasses import dataclass

import pytest

from utils.helpers.user_agent_helpers import _unquote


@dataclass
class Case:
    id: str
    value: str | None
    expected_result: str | None


CASES = [
    Case(id="strips surrounding quotes", value='"Windows"', expected_result="Windows"),
    Case(id="trims whitespace", value="  macOS  ", expected_result="macOS"),
    Case(id="blank becomes none", value="   ", expected_result=None),
    Case(id="none stays none", value=None, expected_result=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__unquote(case: Case):
    assert _unquote(case.value) == case.expected_result
