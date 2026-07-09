from dataclasses import dataclass

import pytest

from utils.helpers.user_agent_helpers import format_client_descriptor

_FIREFOX_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0"
_SAFARI_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
              "(KHTML, like Gecko) Version/17.1 Safari/605.1.15")


@dataclass
class Case:
    id: str
    sec_ch_ua: str | None
    sec_ch_ua_platform: str | None
    user_agent: str | None
    expected_result: str | None


CASES = [
    # client hints: GREASE brand dropped, specific brand preferred over generic "Chromium"
    Case(id="hints-opera-gx",
         sec_ch_ua='"Opera GX";v="131", "Not.A/Brand";v="8", "Chromium";v="147"',
         sec_ch_ua_platform='"Windows"', user_agent=None,
         expected_result="Opera GX 131 (Windows)"),
    Case(id="hints-chrome",
         sec_ch_ua='"Chromium";v="147", "Not.A/Brand";v="8", "Google Chrome";v="147"',
         sec_ch_ua_platform='"macOS"', user_agent=None,
         expected_result="Google Chrome 147 (macOS)"),
    Case(id="hints-edge",
         sec_ch_ua='"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
         sec_ch_ua_platform='"Windows"', user_agent=None,
         expected_result="Microsoft Edge 131 (Windows)"),
    # only GREASE + Chromium present -> fall back to the engine brand
    Case(id="hints-chromium-only",
         sec_ch_ua='"Not.A/Brand";v="8", "Chromium";v="147"',
         sec_ch_ua_platform='"Linux"', user_agent=None,
         expected_result="Chromium 147 (Linux)"),
    # hints win even when a User-Agent is also present
    Case(id="hints-take-precedence-over-ua",
         sec_ch_ua='"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
         sec_ch_ua_platform='"Windows"', user_agent=_FIREFOX_UA,
         expected_result="Google Chrome 147 (Windows)"),
    # hint brand but no platform -> browser only, no parentheses
    Case(id="hints-no-platform",
         sec_ch_ua='"Opera GX";v="131", "Not.A/Brand";v="8", "Chromium";v="147"',
         sec_ch_ua_platform=None, user_agent=None,
         expected_result="Opera GX 131"),
    # UA fallback for hint-less browsers
    Case(id="ua-firefox", sec_ch_ua=None, sec_ch_ua_platform=None, user_agent=_FIREFOX_UA,
         expected_result="Firefox 150 (Windows)"),
    Case(id="ua-safari", sec_ch_ua=None, sec_ch_ua_platform=None, user_agent=_SAFARI_UA,
         expected_result="Safari 17 (macOS)"),
    Case(id="ua-firefox-android", sec_ch_ua=None, sec_ch_ua_platform=None,
         user_agent="Mozilla/5.0 (Android 14; Mobile; rv:150.0) Gecko/150.0 Firefox/150.0",
         expected_result="Firefox 150 (Android)"),
    Case(id="ua-safari-ios", sec_ch_ua=None, sec_ch_ua_platform=None,
         user_agent=("Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 "
                     "(KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"),
         expected_result="Safari 17 (iOS)"),
    # unidentifiable client -> raw User-Agent rather than nothing
    Case(id="ua-unknown-passthrough", sec_ch_ua=None, sec_ch_ua_platform=None,
         user_agent="SomeBot/1.0", expected_result="SomeBot/1.0"),
    Case(id="nothing", sec_ch_ua=None, sec_ch_ua_platform=None, user_agent=None,
         expected_result=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_format_client_descriptor(case: Case):
    assert format_client_descriptor(
        case.sec_ch_ua, case.sec_ch_ua_platform, case.user_agent) == case.expected_result
