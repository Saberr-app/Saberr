import re

_SEC_CH_UA_ENTRY = re.compile(r'"([^"]+)";\s*v="([^"]*)"')


def format_client_descriptor(sec_ch_ua: str | None,
                             sec_ch_ua_platform: str | None,
                             user_agent: str | None) -> str | None:
    """Build a concise "Browser (Platform)" descriptor for a client.

    Prefers User-Agent Client Hints (sent only by Chromium browsers over secure contexts) and falls
    back to parsing the User-Agent string for browsers that don't send hints (Firefox, Safari). If
    the browser can't be identified at all, the raw User-Agent is returned rather than nothing.
    """
    browser = _browser_from_client_hints(sec_ch_ua) or _browser_from_user_agent(user_agent)
    platform = _unquote(sec_ch_ua_platform) or _platform_from_user_agent(user_agent)
    if not browser:
        return user_agent
    return f"{browser} ({platform})" if platform else browser


def _browser_from_client_hints(sec_ch_ua: str | None) -> str | None:
    if not sec_ch_ua:
        return None
    brands = _SEC_CH_UA_ENTRY.findall(sec_ch_ua)
    real = [(name.strip(), version) for name, version in brands if not _is_grease(name)]
    if not real:
        return None
    # prefer the specific browser brand over the generic "Chromium" engine entry
    name, version = next((brand for brand in real if brand[0].lower() != "chromium"), real[0])
    return f"{name} {version}" if version else name


def _is_grease(brand: str) -> bool:
    # Chromium injects a deliberately varied "GREASE" brand (e.g. "Not.A/Brand", "Not)A;Brand")
    low = brand.lower()
    return "not" in low and "brand" in low


def _browser_from_user_agent(user_agent: str | None) -> str | None:
    if not user_agent:
        return None
    # priority order; Edge/Opera must precede Chrome since their UAs also contain "Chrome"
    for label, pattern in (("Firefox", r"Firefox/(\d+)"),
                           ("Edge", r"Edg(?:e|A|iOS)?/(\d+)"),
                           ("Opera", r"OPR/(\d+)"),
                           ("Chrome", r"Chrome/(\d+)")):
        if match := re.search(pattern, user_agent):
            return f"{label} {match.group(1)}"
    # Safari carries its version in "Version/" and, unlike Chromium browsers, has no "Chrome" token
    if "Safari" in user_agent and "Chrome" not in user_agent and "Chromium" not in user_agent:
        if match := re.search(r"Version/(\d+)", user_agent):
            return f"Safari {match.group(1)}"
    return None


def _platform_from_user_agent(user_agent: str | None) -> str | None:
    if not user_agent:
        return None
    if "Windows" in user_agent:
        return "Windows"
    if "Android" in user_agent:  # check before Linux: Android UAs also contain "Linux"
        return "Android"
    if "iPhone" in user_agent or "iPad" in user_agent:
        return "iOS"
    if "Mac OS X" in user_agent or "Macintosh" in user_agent:
        return "macOS"
    if "Linux" in user_agent:
        return "Linux"
    return None


def _unquote(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().strip('"') or None
