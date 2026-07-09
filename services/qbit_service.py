from typing import Iterable
from uuid import uuid4

from common.exceptions import ExternalServiceException
from config import config
from dto.http_response import StandardResponse
from services import ThirdPartyService, reauthenticate_on_error_codes


class QBitService(ThirdPartyService):

    class Endpoint:
        LOGIN = "/api/v2/auth/login"
        TORRENTS_INFO = "/api/v2/torrents/info"
        TORRENTS_ADD = "/api/v2/torrents/add"
        TORRENTS_START = "/api/v2/torrents/start"
        TORRENTS_DELETE = "/api/v2/torrents/delete"
        HEALTHCHECK = "/api/v2/app/version"

    @property
    def base_url(self) -> str:
        return self._base_url or config.user_settings.qbit_base_url

    @property
    def username(self) -> str:
        return self._username or config.user_settings.qbit_username

    @property
    def password(self) -> str:
        return self._password or config.user_settings.qbit_password

    def __init__(self, base_url: str | None = None, username: str | None = None, password: str | None = None):
        super().__init__()
        self._base_url = base_url
        self._username = username
        self._password = password

    async def authenticate(self, session_name: str | None = None):
        url = self.base_url + self.Endpoint.LOGIN
        response = await self._request("POST", url,
                                       data={
                                           'username': self.username,
                                           'password': self.password
                                       } if self.username else {},
                                       session_name=session_name)
        # cookie name is inconsistent across different qbit versions it seems (SID on win, QBT_SID_port on linux),
        # so it can't be reliably and explicitly checked, response text also differs ('Ok.' on windows, empty on linux)
        if response.status in range(200, 300) and response.cookies:
            return
        raise ExternalServiceException(f"Authentication failed with qBittorrent WebUI. "
                                       f"Check credentials ({response.status_code}: {response.text}).",
                                       status_code=response.status_code)

    @reauthenticate_on_error_codes(range(400, 500))
    async def get_torrents(self, hashes: Iterable[str] = None,
                           sort: str = "added_on",
                           sort_desc: bool = True):
        self.logger.debug(f"Getting torrents with hashes: {hashes}")
        url = self.base_url + self.Endpoint.TORRENTS_INFO
        params = {
            'sort': sort,
            'reverse': "true" if sort_desc else "false"
        }
        if hashes:
            params['hashes'] = '|'.join(hashes)
        response = await self._request("GET", url, params=params)
        return response.json

    @reauthenticate_on_error_codes(range(400, 500))
    async def add_torrents(self, torrent_or_magnet_links: list[str],
                           save_path: str | None,
                           category: str | None = None,
                           tags: list[str] | None = None,
                           create_root_folder: bool = True) -> str:
        self.logger.debug(f"Adding torrents: {torrent_or_magnet_links}")
        url = self.base_url + self.Endpoint.TORRENTS_ADD
        data = {
            'urls': '\n'.join(torrent_or_magnet_links),
            'category': category or "",
            'tags': ','.join(tags) if tags else "",
        }
        if save_path:
            data |= {
                'savepath': save_path,
                'root_folder': "true" if create_root_folder else "false"
            }
        response = await self._request("POST", url, data=data)
        return self._process_response(response).text

    @reauthenticate_on_error_codes(range(400, 500))
    async def start_torrents(self, hashes: list[str]) -> str:
        self.logger.debug(f"Starting torrents: {hashes}")
        url = self.base_url + self.Endpoint.TORRENTS_START
        data = {"hashes": "|".join(hashes)}
        response = await self._request("POST", url, data=data)
        return self._process_response(response).text

    @reauthenticate_on_error_codes(range(400, 500))
    async def delete_torrents(self, hashes: list[str], delete_files: bool = False) -> str:
        self.logger.debug(f"Deleting torrents: {hashes}")
        url = self.base_url + self.Endpoint.TORRENTS_DELETE
        data = {"hashes": "|".join(hashes), "deleteFiles": "true" if delete_files else "false"}
        response = await self._request("POST", url, data=data)
        return self._process_response(response).text

    async def healthcheck(self, use_new_session: bool = False):
        session_name = uuid4().hex if use_new_session else None
        url = self.base_url + self.Endpoint.HEALTHCHECK
        response = await self._request("GET", url, session_name=session_name)
        if response.status_code in range(400, 500):
            await self.authenticate(session_name=session_name)
            response = await self._request("GET", url, session_name=session_name)
        if response.status_code not in range(200, 300):
            raise ExternalServiceException(
                detail=response.text if response.status_code in range(400, 500) else "QBit is down",
                status_code=response.status_code
            )

    # noinspection PyMethodMayBeStatic
    def _process_response(self, response) -> StandardResponse:
        if response.status == 404:
            raise ExternalServiceException("Not found",
                                           status_code=response.status,
                                           debug_info={
                                               "url": response.url,
                                               "status": response.status,
                                               "content": response.text,
                                               "headers": response.headers
                                           })
        elif response.status >= 500:
            raise ExternalServiceException("QBit is down",
                                           status_code=response.status,
                                           debug_info={
                                               "url": response.url,
                                               "status": response.status,
                                               "content": response.text,
                                               "headers": response.headers
                                           })
        elif response.status not in range(200, 300):
            raise ExternalServiceException(f"Unhandled response from QBit ({response.status}): {response.text}",
                                           status_code=response.status,
                                           debug_info={
                                               "url": response.url,
                                               "content": response.text,
                                               "headers": response.headers
                                           })

        return response
