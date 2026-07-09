from dataclasses import dataclass

import pytest

from utils.helpers.file_name_formatters import _are_continuous


@dataclass
class Case:
    id: str
    numbers: list[int]
    expected_result: bool


CASES = [
    Case(id="consecutive ascending", numbers=[1, 2, 3], expected_result=True),
    Case(id="unsorted but consecutive", numbers=[3, 1, 2], expected_result=True),
    Case(id="gap breaks continuity", numbers=[1, 3], expected_result=False),
    Case(id="single number is continuous", numbers=[5], expected_result=True),
    Case(id="empty is continuous", numbers=[], expected_result=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__are_continuous(case: Case):
    assert _are_continuous(case.numbers) == case.expected_result
