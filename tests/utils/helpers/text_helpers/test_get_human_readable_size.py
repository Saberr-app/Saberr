from dataclasses import dataclass

import pytest

from utils.helpers.text_helpers import get_human_readable_size


@dataclass
class Case:
    id: str
    size: int
    expected_result: str
    precision: int = 2


CASES = [
    Case(id="zero bytes", size=0, expected_result="0 B"),
    Case(id="bytes below 1 KB", size=512, expected_result="512 B"),
    Case(id="just under 1 KB", size=1023, expected_result="1023 B"),
    Case(id="exactly 1 KB", size=1024, expected_result="1.00 KB"),
    Case(id="1.5 KB", size=1536, expected_result="1.50 KB"),
    Case(id="1 MB", size=1024 ** 2, expected_result="1.00 MB"),
    Case(id="1 GB", size=1024 ** 3, expected_result="1.00 GB"),
    Case(id="1 TB", size=1024 ** 4, expected_result="1.00 TB"),
    Case(id="custom precision 1", size=1536, precision=1, expected_result="1.5 KB"),
    Case(id="custom precision 0 rounds", size=1536, precision=0, expected_result="2 KB"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_get_human_readable_size(case: Case):
    assert get_human_readable_size(case.size, precision=case.precision) == case.expected_result
