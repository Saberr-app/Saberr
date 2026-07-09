from dataclasses import dataclass

import pytest

from utils.helpers.text_helpers import is_valid_url


@dataclass
class Case:
    id: str
    url: str
    expected_result: bool


CASES = [
    Case(id="http host", url="http://example.com", expected_result=True),
    Case(id="https host", url="https://example.com", expected_result=True),
    Case(id="path query fragment", url="https://example.com/path?q=1#frag", expected_result=True),
    Case(id="subdomain with port and path", url="http://sub.domain.co.uk:443/x", expected_result=True),
    Case(id="localhost", url="http://localhost", expected_result=True),
    Case(id="localhost with port", url="http://localhost:8080", expected_result=True),
    Case(id="localhost with port and path", url="https://localhost:8080/api", expected_result=True),
    Case(id="ipv4", url="http://192.168.1.1", expected_result=True),
    Case(id="ipv4 with port and path", url="http://192.168.1.1:8080/api", expected_result=True),
    # a scheme is required, so bare hosts/IPs (even with a port) are rejected
    Case(id="bare localhost", url="localhost", expected_result=False),
    Case(id="bare localhost with port", url="localhost:8080", expected_result=False),
    Case(id="bare host", url="example.com", expected_result=False),
    Case(id="bare ipv4 with port", url="192.168.1.1:8080", expected_result=False),
    Case(id="unsupported scheme", url="ftp://example.com", expected_result=False),
    Case(id="scheme only", url="http://", expected_result=False),
    Case(id="space in host", url="http://exa mple.com", expected_result=False),
    Case(id="not a url", url="not a url", expected_result=False),
    Case(id="empty string", url="", expected_result=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_is_valid_url(case: Case):
    assert is_valid_url(case.url) is case.expected_result
