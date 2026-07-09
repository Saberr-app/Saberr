from dataclasses import dataclass

import pytest

from utils.helpers.text_helpers import shorten_text


@dataclass
class Case:
    id: str
    text: str
    max_length: int
    expected_result: str


CASES = [
    Case(id="shorter than limit -> unchanged", text="hello", max_length=10, expected_result="hello"),
    Case(id="exactly the limit -> unchanged", text="hello", max_length=5, expected_result="hello"),
    Case(id="truncates with ellipsis", text="hello world", max_length=8, expected_result="hello..."),
    Case(id="ellipsis eats into the limit", text="abcdefghij", max_length=6, expected_result="abc..."),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_shorten_text(case: Case):
    assert shorten_text(case.text, case.max_length) == case.expected_result
