from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from common.db import session_context, get_session, execute_post_commit_actions, execute_post_rollback_actions

DB_SESSION_PREFIXES = ("/api/v1",)
DB_SESSION_SKIP_PREFIXES = ("/api/v1/docs", "/api/v1/healthcheck")


class DBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(DB_SESSION_PREFIXES):
            if request.url.path.startswith(DB_SESSION_SKIP_PREFIXES):
                return await call_next(request)
            async with session_context():
                try:
                    response = await call_next(request)
                except Exception as e:
                    await get_session().rollback()
                    await execute_post_rollback_actions()
                    raise e from e
                else:
                    await get_session().commit()
                    await execute_post_commit_actions()
                return response
        return await call_next(request)
