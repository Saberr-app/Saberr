from dataclasses import dataclass

import pytest

from utils.helpers.user_agent_helpers import _platform_from_user_agent


@dataclass
class Case:
    id: str
    user_agent: str | None
    expected_result: str | None


CASES = [
    Case(id="windows", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)", expected_result="Windows"),
    # Android UAs also contain "Linux"; Android must win
    Case(id="android precedes linux", user_agent="Mozilla/5.0 (Linux; Android 13)", expected_result="Android"),
    Case(id="iphone", user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)", expected_result="iOS"),
    Case(id="macos", user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", expected_result="macOS"),
    Case(id="linux", user_agent="Mozilla/5.0 (X11; Linux x86_64)", expected_result="Linux"),
    Case(id="none returns none", user_agent=None, expected_result=None),
    Case(id="unknown returns none", user_agent="curl/8.0", expected_result=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__platform_from_user_agent(case: Case):
    assert _platform_from_user_agent(case.user_agent) == case.expected_result
