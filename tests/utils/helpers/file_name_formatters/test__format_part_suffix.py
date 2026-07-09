from dataclasses import dataclass

import pytest

from utils.helpers.file_name_formatters import _format_part_suffix


@dataclass
class Case:
    id: str
    part_numbers: list[int]
    expected_result: str


CASES = [
    Case(id="single part", part_numbers=[2], expected_result=" Part 2"),
    Case(id="continuous range", part_numbers=[1, 2, 3], expected_result=" Part 1-3"),
    Case(id="unsorted continuous range", part_numbers=[3, 1, 2], expected_result=" Part 1-3"),
    Case(id="non-continuous parts joined", part_numbers=[1, 3], expected_result=" Part 1&3"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__format_part_suffix(case: Case):
    assert _format_part_suffix(case.part_numbers) == case.expected_result
