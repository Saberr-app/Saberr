import aiohttp
import requests
from datetime import datetime, timedelta, UTC

from aiohttp_socks import ProxyConnector

from dto.proxy_config import ProxyConfig

_async_http_sessions: dict[str, tuple[aiohttp.ClientSession, datetime]] = {
    # name: (session, expiry datetime)
}

_sync_http_sessions: dict[str, tuple[requests.Session, datetime]] = {
    # name: (session, expiry datetime)
}


async def get_async_http_session(name: str, session_lifetime: int = 60*60*4, proxy_config: ProxyConfig | None = None):
    """
    Get or create an asynchronous HTTP session
    Args:
        name (str): The identifier of the session.
        session_lifetime (int): The lifetime of the session in seconds. Defaults to 4 hours.
        proxy_config (ProxyConfig | None): The proxy configuration to use for the session.
    Returns:
        aiohttp.ClientSession: The asynchronous HTTP session.
    """
    key = name if not proxy_config else f"{name}|{hash(proxy_config.as_str())}"
    if key in _async_http_sessions:
        session, expiry = _async_http_sessions[key]
        if not session.closed:
            if expiry < datetime.now(UTC):
                await session.close()
            else:
                return session
    connector = ProxyConnector.from_url(proxy_config.as_str(), rdns=True) if proxy_config else None
    session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True), connector=connector)
    expiry = datetime.now(UTC) + timedelta(seconds=session_lifetime)
    _async_http_sessions[key] = (session, expiry)
    return session


def get_sync_http_session(name: str):
    """
    Get or create a synchronous HTTP session
    Args:
        name (str): The identifier of the session.
    Returns:
        requests.Session: The synchronous HTTP session.
    """
    if name in _sync_http_sessions:
        session, expiry = _sync_http_sessions[name]
        if expiry > datetime.now(UTC):
            return session
        session.close()
    session = requests.Session()
    expiry = datetime.now(UTC) + timedelta(minutes=30)
    _sync_http_sessions[name] = (session, expiry)
    return session
