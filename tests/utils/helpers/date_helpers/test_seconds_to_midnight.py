from dataclasses import dataclass
from datetime import datetime, UTC

import pytest

from utils.helpers import date_helpers
from utils.helpers.date_helpers import seconds_to_midnight


@dataclass
class Case:
    id: str
    now: datetime
    expected_result: int


CASES = [
    Case(id="two hours before midnight", now=datetime(2024, 6, 15, 22, 0, 0, tzinfo=UTC),
         expected_result=7200),
    Case(id="one second past midnight is almost a full day", now=datetime(2024, 6, 15, 0, 0, 1, tzinfo=UTC),
         expected_result=86399),
    # sub-second remainder truncates toward zero
    Case(id="half a second before midnight truncates to zero",
         now=datetime(2024, 6, 15, 23, 59, 59, 500000, tzinfo=UTC), expected_result=0),
    Case(id="midday on the last day of the year", now=datetime(2024, 12, 31, 12, 0, 0, tzinfo=UTC),
         expected_result=43200),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_seconds_to_midnight(case: Case, mocker):
    # freeze now() but keep the real datetime constructor the function uses for midnight
    fake = mocker.patch.object(date_helpers, "datetime")
    fake.now.return_value = case.now
    fake.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    assert seconds_to_midnight() == case.expected_result
