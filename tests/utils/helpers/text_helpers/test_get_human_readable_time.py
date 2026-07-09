from dataclasses import dataclass

import pytest

from utils.helpers.text_helpers import get_human_readable_time


@dataclass
class Case:
    id: str
    seconds: int
    expected_result: str
    minimal: bool = True


CASES = [
    Case(id="1 second", seconds=1, expected_result="1s"),
    Case(id="1 minute", seconds=60, expected_result="1m"),
    Case(id="minute and seconds", seconds=90, expected_result="1m 30s"),
    Case(id="1 hour", seconds=3600, expected_result="1h"),
    Case(id="hour minute second", seconds=3661, expected_result="1h 1m 1s"),
    Case(id="1 day", seconds=86400, expected_result="1d"),
    Case(id="1 week", seconds=604800, expected_result="1w"),
    Case(id="1 month uses 'mo'", seconds=2592000, expected_result="1mo"),
    Case(id="1 year", seconds=31536000, expected_result="1y"),
    Case(id="month and minute do not collide", seconds=2592000 + 60, expected_result="1mo 1m"),
    Case(id="verbose 1 second", seconds=1, minimal=False, expected_result="1 second"),
    Case(id="verbose plural seconds", seconds=2, minimal=False, expected_result="2 seconds"),
    Case(id="verbose hour minute second", seconds=3661, minimal=False,
         expected_result="1 hour, 1 minute, 1 second"),
    Case(id="verbose 1 month", seconds=2592000, minimal=False, expected_result="1 month"),
    Case(id="zero is unresolved", seconds=0, expected_result="Unresolved"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_get_human_readable_time(case: Case):
    assert get_human_readable_time(case.seconds, minimal=case.minimal) == case.expected_result
