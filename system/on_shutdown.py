from common.http_session import _sync_http_sessions, _async_http_sessions  # noqa
from common.db import engine
from common.logging_config import stop_logging


async def on_shutdown_actions():
    for _, (session, _) in _sync_http_sessions.items():
        session.close()
    for _, (session, _) in _async_http_sessions.items():
        await session.close()

    await engine.dispose()
    stop_logging()
