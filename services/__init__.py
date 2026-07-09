"""
Base class for third party services where applicable.
"""
# noinspection PyPackageRequirements
import contextvars
import hashlib
import json
import logging
from datetime import timedelta, datetime, UTC
from functools import wraps
from typing import Iterable

from aiohttp import FormData,  ClientError

from app_state import CACHED_RESPONSES
from common.exceptions import ExternalServiceException
from common.http_session import get_async_http_session, get_sync_http_session
from dto.http_response import StandardResponse


class ThirdPartyService:
    BASE_URL = None
    LOG_REQUESTS = True

    class Endpoint:
        # to be overridden by child classes
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)
        # as context var in case an isolated task was created within the same component
        self._cache_hit = contextvars.ContextVar("_cache_hit", default=False)

    def __new__(cls, *args, **kwargs):
        if cls is ThirdPartyService:
            raise TypeError("ThirdPartyService class cannot be instantiated.")
        return super().__new__(cls)

    def cache_hit_on_last_request(self) -> bool:
        return self._cache_hit.get()

    async def _request(self,
                       method: str,
                       url: str,
                       json_: dict | None = None,
                       headers: dict | None = None,
                       params: dict | None = None,
                       data: dict | FormData | None = None,
                       force_fetch: bool = False,
                       cache_duration: int = 0,
                       session_name: str | None = None) -> 'StandardResponse':
        if force_fetch or not (standard_response := self._get_cached_response(
            method=method, url=url, json_=json_, headers=headers, params=params, data=data
        )):
            if self.LOG_REQUESTS:
                self.logger.debug(f"Making `{method}` request to `{url}`")
            if session_name:
                session = await get_async_http_session(session_name, session_lifetime=60*10)
            else:
                session = await get_async_http_session(name=self.__class__.__name__)
            try:
                async with session.request(method=method, url=url, json=json_,
                                           headers=headers, params=params, data=data) as response:
                    standard_response = await StandardResponse.from_aiohttp_response(response)
            except ClientError as e:
                raise ExternalServiceException(f"Failed to connect: {e}", status_code=500) from e
            self._handle_caching(standard_response=standard_response, cache_duration=cache_duration,
                                 data=data, method=method, url=url, json_=json_,
                                 headers=headers, params=params)
            self._cache_hit.set(False)
        else:
            if self.LOG_REQUESTS:
                self.logger.debug(f"Using cached response for `{method}` request to `{url}`.")
            self._cache_hit.set(True)
        return standard_response

    def _sync_request(self,
                      method: str,
                      url: str,
                      json_: dict | None = None,
                      headers: dict | None = None,
                      params: dict | None = None,
                      data: dict | None = None,
                      files: list[tuple[str, bytes]] | None = None,
                      cache_duration: int = 0) -> 'StandardResponse':
        if not (standard_response := self._get_cached_response(
            method=method, url=url, json_=json_, headers=headers, params=params, data=data
        )):
            if self.LOG_REQUESTS:
                self.logger.debug(f"Making `{method}` request to `{url}`")
            session = get_sync_http_session(name=self.__class__.__name__)
            with session.request(method=method, url=url, json=json_,
                                 headers=headers, params=params, data=data, files=files) as response:
                standard_response = StandardResponse.from_requests_response(response)
            self._handle_caching(standard_response=standard_response, cache_duration=cache_duration,
                                 data=data, method=method, url=url, json_=json_, headers=headers, params=params)
        else:
            if self.LOG_REQUESTS:
                self.logger.debug(f"Using cached response for `{method}` request to `{url}`")
        return standard_response

    # noinspection PyMethodMayBeStatic
    def _get_cached_response(self,
                             method: str,
                             url: str,
                             json_: dict | None = None,
                             headers: dict | None = None,
                             params: dict | None = None,
                             data: dict | None = None) -> 'StandardResponse | None':
        cache_key = self._build_cache_key(method=method, url=url, json_=json_,
                                          headers=headers, params=params, data=data)
        cached_response = CACHED_RESPONSES.get(cache_key)
        if cached_response and cached_response.cache_expiry < datetime.now(UTC):
            return None
        return cached_response

    # noinspection PyMethodMayBeStatic
    def _handle_caching(self,
                        standard_response: 'StandardResponse',
                        cache_duration: int,
                        data: dict | None,
                        method: str,
                        url: str,
                        json_: dict | None,
                        headers: dict | None,
                        params: dict | None) -> None:
        if not cache_duration or standard_response.status_code >= 400:
            return
        cache_key = self._build_cache_key(method=method, url=url, json_=json_,
                                          headers=headers, params=params, data=data)
        standard_response.cache_expiry = datetime.now(UTC) + timedelta(seconds=cache_duration)
        CACHED_RESPONSES[cache_key] = standard_response

    @staticmethod
    def _build_cache_key(method: str,
                         url: str,
                         json_: dict | None = None,
                         headers: dict | None = None,
                         params: dict | None = None,
                         data: dict | None = None) -> str:
        def _serialize(value: dict | None) -> str:
            if value is None:
                return ""
            return json.dumps(value, sort_keys=True, default=str)

        raw_key = f"{method}|{url}|{_serialize(json_)}|{_serialize(headers)}|" \
                  f"{_serialize(params)}|{_serialize(data)}"
        return hashlib.sha256(raw_key.encode()).hexdigest()


def reauthenticate_on_error_codes(codes: Iterable[int]):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except ExternalServiceException as e:
                if e.status_code in codes:
                    await self.authenticate()
                    return await func(self, *args, **kwargs)
                raise e
        return wrapper
    return decorator
