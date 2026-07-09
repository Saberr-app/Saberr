from dataclasses import dataclass

import pytest

from constants import EpisodeFormattingToken
from utils.helpers.file_name_formatters import _format_numbers_with_parts

_EN = EpisodeFormattingToken.EPISODE_NUMBER.value
_PREFIXED = "E{" + _EN + "}"


@dataclass
class Case:
    id: str
    numbers: list[int]
    part_numbers: list[int] | None
    padding: int
    expected_result: str


CASES = [
    Case(id="numbers only", numbers=[5], part_numbers=None, padding=2, expected_result="05"),
    Case(id="continuous range with a part suffix", numbers=[1, 2, 3], part_numbers=[2], padding=2,
         expected_result="01-E03 Part 2"),
    Case(id="single number with a continuous part range", numbers=[7], part_numbers=[1, 2], padding=2,
         expected_result="07 Part 1-2"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__format_numbers_with_parts(case: Case):
    result = _format_numbers_with_parts(_PREFIXED, case.numbers, case.part_numbers, case.padding)
    assert result == case.expected_result
