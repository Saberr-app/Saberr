import json
from datetime import datetime

import aiohttp
import requests
from requests.cookies import RequestsCookieJar
from requests.structures import CaseInsensitiveDict


class StandardResponse:
    def __init__(self,
                 original_response: aiohttp.ClientResponse | requests.Response,
                 status: int,
                 url: str,
                 json_: dict | None = None,
                 text: str | None = None,
                 content: bytes | None = None,
                 headers: CaseInsensitiveDict | None = None,
                 cookies: RequestsCookieJar | dict | None = None):
        self.original_response: aiohttp.ClientResponse | requests.Response = original_response
        self.status: int = status
        self.status_code: int = status  # alias
        self.url: str = url
        self.json: dict | None = json_
        self.text: str | None = text
        self.content: bytes | None = content
        self.headers: CaseInsensitiveDict = headers
        self.cookies: dict | None = cookies
        self.cache_expiry: datetime | None = None  # to be set when caching is applied

    @staticmethod
    async def from_aiohttp_response(response: aiohttp.ClientResponse) -> 'StandardResponse':
        try:
            text = await response.text()
        except Exception:
            text = None
        try:
            content = await response.read()
        except Exception:
            content = None
        try:
            json_ = await response.json()
        except Exception:
            try:
                json_ = json.loads(text)
            except Exception:
                json_ = None
        return StandardResponse(original_response=response, status=response.status, url=str(response.url),
                                json_=json_, text=text, content=content, headers=response.headers,
                                cookies={cookie: cookie_value.value
                                         for cookie, cookie_value in response.cookies.items()})

    @staticmethod
    def from_requests_response(response: requests.Response) -> 'StandardResponse':
        try:
            json_ = response.json()
        except Exception:
            json_ = None
        return StandardResponse(original_response=response, status=response.status_code, url=response.url,
                                json_=json_, text=response.text, content=response.content,
                                headers=response.headers, cookies=response.cookies)

    def __repr__(self):
        return f"<StandardResponse status_code={self.status_code} url={self.url}>"
