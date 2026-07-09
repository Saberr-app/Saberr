from dataclasses import dataclass

import pytest

from utils.helpers.user_agent_helpers import _browser_from_client_hints


@dataclass
class Case:
    id: str
    sec_ch_ua: str | None
    expected_result: str | None


CASES = [
    Case(id="prefers the specific brand over chromium",
         sec_ch_ua='"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
         expected_result="Google Chrome 122"),
    Case(id="falls back to chromium when no specific brand",
         sec_ch_ua='"Chromium";v="122", "Not.A/Brand";v="24"',
         expected_result="Chromium 122"),
    Case(id="none header returns none", sec_ch_ua=None, expected_result=None),
    Case(id="only grease brands returns none",
         sec_ch_ua='"Not.A/Brand";v="24"', expected_result=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__browser_from_client_hints(case: Case):
    assert _browser_from_client_hints(case.sec_ch_ua) == case.expected_result
