import logging
import traceback

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from common.exceptions import BaseAPIException

_logger = logging.getLogger(__name__)


class ResponseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
        except BaseAPIException as e:
            response = JSONResponse(content={"detail": e.detail,
                                             "code": e.code},
                                    status_code=e.status_code)
        except Exception as e:
            _logger.exception(f"Unexpected exception while handling request ({request.method} {request.url}): {e}")
            response = JSONResponse(content={"detail": "Something went wrong. Check the logs.",
                                             "code": "INTERNAL_SERVER_ERROR"},
                                    status_code=500)
        return response
