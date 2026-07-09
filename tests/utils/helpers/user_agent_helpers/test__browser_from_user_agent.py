from dataclasses import dataclass

import pytest

from utils.helpers.user_agent_helpers import _browser_from_user_agent

_FIREFOX = "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
_CHROME = "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/122.0 Safari/537.36"
_EDGE = "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/122.0 Safari/537.36 Edg/122.0"
_OPERA = "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/122.0 Safari/537.36 OPR/108.0"
_SAFARI = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15"


@dataclass
class Case:
    id: str
    user_agent: str | None
    expected_result: str | None


CASES = [
    Case(id="firefox", user_agent=_FIREFOX, expected_result="Firefox 120"),
    Case(id="chrome", user_agent=_CHROME, expected_result="Chrome 122"),
    # Edge/Opera UAs also contain "Chrome" and must win over it
    Case(id="edge precedes chrome", user_agent=_EDGE, expected_result="Edge 122"),
    Case(id="opera precedes chrome", user_agent=_OPERA, expected_result="Opera 108"),
    Case(id="safari has no chrome token", user_agent=_SAFARI, expected_result="Safari 17"),
    Case(id="none returns none", user_agent=None, expected_result=None),
    Case(id="unknown returns none", user_agent="curl/8.0", expected_result=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__browser_from_user_agent(case: Case):
    assert _browser_from_user_agent(case.user_agent) == case.expected_result
