from common.exceptions import ExternalServiceException
from constants import TVDBSeasonType, TV_PUBLIC_API_KEY as TVDB_API_KEY
from services import ThirdPartyService, reauthenticate_on_error_codes


class TVDBService(ThirdPartyService):
    BASE_URL = "https://api4.thetvdb.com/v4"

    class Endpoint:
        LOGIN = "/login"
        SEARCH = "/search"
        SERIES_EPISODES = "/series/{series_id}/episodes/{season_type}/{language_code}"
        SERIES = "/series/{series_id}/extended?short=true"
        SERIES_TRANSLATIONS = "/series/{series_id}/translations/{language_code}"
        HEALTHCHECK = "/user"

    def __init__(self):
        super().__init__()
        self._api_key = TVDB_API_KEY
        self._bearer_token = None

    async def authenticate(self):
        url = self.BASE_URL + self.Endpoint.LOGIN
        response = await self._request("POST", url, json_={"apikey": self._api_key})
        response = self._process_response(response)
        self._bearer_token = response["data"]["token"]

    async def get_auth_headers(self):
        if not self._bearer_token:
            await self.authenticate()
        return {"Authorization": self._bearer_token}

    @reauthenticate_on_error_codes([401, 403])
    async def search_series(self, query: str, force_fetch: bool = False) -> list:
        self.logger.debug(f"Searching for series: {query}")
        url = self.BASE_URL + self.Endpoint.SEARCH
        response = await self._request("GET", url,
                                       headers=await self.get_auth_headers(),
                                       params={"query": query, "type": "series"},
                                       cache_duration=60*60*6,
                                       force_fetch=force_fetch)
        return self._process_response(response)["data"]

    @reauthenticate_on_error_codes([401, 403])
    async def get_series_episodes(self, series_id: int, season_type: TVDBSeasonType,
                                  language_code: str = "eng", page: int = 0) -> dict:
        self.logger.debug(f"Getting episodes for series {series_id} ({season_type.value})")
        url = self.BASE_URL + self.Endpoint.SERIES_EPISODES.format(series_id=series_id,
                                                                   season_type=season_type.value,
                                                                   language_code=language_code)
        response = await self._request("GET", url,
                                       headers=await self.get_auth_headers(),
                                       params={"page": page})
        return self._process_response(response)

    @reauthenticate_on_error_codes([401, 403])
    async def get_series(self, series_id: int) -> dict:
        self.logger.debug(f"Getting series {series_id}")
        url = self.BASE_URL + self.Endpoint.SERIES.format(series_id=series_id)
        response = await self._request("GET", url,
                                       headers=await self.get_auth_headers())
        return self._process_response(response)

    @reauthenticate_on_error_codes([401, 403])
    async def get_series_translations(self, series_id: int, language_code: str = "eng") -> dict:
        self.logger.debug(f"Getting translations for series {series_id}")
        url = self.BASE_URL + self.Endpoint.SERIES_TRANSLATIONS.format(series_id=series_id,
                                                                       language_code=language_code)
        response = await self._request("GET", url,
                                       headers=await self.get_auth_headers())
        return self._process_response(response)

    async def healthcheck(self):
        url = self.BASE_URL + self.Endpoint.HEALTHCHECK
        response = await self._request("GET", url, headers=await self.get_auth_headers())
        if response.status_code in range(400, 500):
            await self.authenticate()
            response = await self._request("GET", url, headers=await self.get_auth_headers())
        if response.status_code not in range(200, 300):
            raise ExternalServiceException(
                detail=response.text if response.status_code in range(400, 500) else "TVDB is down",
                status_code=response.status_code
            )

    # noinspection PyMethodMayBeStatic
    def _process_response(self, response) -> dict:
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
            raise ExternalServiceException("TheTVDB is down",
                                           status_code=response.status,
                                           debug_info={
                                               "url": response.url,
                                               "status": response.status,
                                               "content": response.text,
                                               "headers": response.headers
                                           })
        elif response.status != 200:
            raise ExternalServiceException(f"Unhandled response from TheTVDB ({response.status}): {response.text}",
                                           status_code=response.status,
                                           debug_info={
                                               "url": response.url,
                                               "content": response.text,
                                               "headers": response.headers
                                           })

        return response.json
