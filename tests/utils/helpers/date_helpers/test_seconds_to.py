from dataclasses import dataclass
from datetime import datetime, UTC

import pytest

from utils.helpers import date_helpers
from utils.helpers.date_helpers import seconds_to


@dataclass
class Case:
    id: str
    now: datetime
    hour: int
    expected_result: int
    minute: int = 0
    local: bool = True


CASES = [
    Case(id="local target later today", now=datetime(2024, 6, 15, 20, 0, 0), hour=21, expected_result=3600),
    Case(id="local target already passed rolls to tomorrow", now=datetime(2024, 6, 15, 22, 0, 0), hour=21,
         expected_result=23 * 3600),
    Case(id="exactly at target rolls to tomorrow", now=datetime(2024, 6, 15, 21, 0, 0), hour=21,
         expected_result=86400),
    Case(id="minute is honoured", now=datetime(2024, 6, 15, 20, 0, 0), hour=21, minute=30,
         expected_result=5400),
    Case(id="sub-second remainder truncates toward zero", now=datetime(2024, 6, 15, 20, 59, 59, 500000), hour=21,
         expected_result=0),
    Case(id="utc target later today", now=datetime(2024, 6, 15, 20, 0, 0, tzinfo=UTC), hour=21, local=False,
         expected_result=3600),
    Case(id="utc target already passed rolls to tomorrow", now=datetime(2024, 12, 31, 23, 0, 0, tzinfo=UTC),
         hour=1, local=False, expected_result=2 * 3600),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_seconds_to(case: Case, mocker):
    fake = mocker.patch.object(date_helpers, "datetime")
    # local mode calls now() and then astimezone(), which keeps the wall-clock time in the host timezone
    fake.now.side_effect = lambda tz=None: case.now if tz is not None else case.now.replace(tzinfo=None)

    assert seconds_to(hour=case.hour, minute=case.minute, local=case.local) == case.expected_result