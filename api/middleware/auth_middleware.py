import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from constants import JWT_ALGORITHM
from common.exceptions import UnauthorizedException
from config import config

_AUTH_PREFIXES = ("/api/v1",)
_AUTH_SKIP_ROUTES = ("/api/v1/login", "/api/v1/credentials-status",
                     "/api/v1/credentials-setup", "/api/v1/request-password-reset",
                     "/api/v1/reset-password", "/api/v1/healthcheck")


class AuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if not path.startswith(_AUTH_PREFIXES) or path in _AUTH_SKIP_ROUTES:
            return await call_next(request)

        if "authorization" not in request.headers:
            raise UnauthorizedException("Missing Authorization header", code="MISSING_AUTH_HEADER")
        scheme, _, token = request.headers["authorization"].partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise UnauthorizedException("Malformed Authorization header", code="MALFORMED_AUTH_HEADER")
        try:
            jwt.decode(token, config.jwt_secret, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise UnauthorizedException("Token has expired", code="TOKEN_EXPIRED")
        except jwt.InvalidTokenError:
            raise UnauthorizedException("Invalid token", "INVALID_TOKEN")

        return await call_next(request)
