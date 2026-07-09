from common.exceptions import ExternalServiceException
from config import config
from constants import RSS_CATEGORY_TO_CODE_MAP
from services import ThirdPartyService, StandardResponse


class RSSService(ThirdPartyService):
    BASE_URL = "https://nyaa.si/"

    class Endpoint:
        RSS = "?page=rss&q={query}&c={category_code}&f=0"

    def __init__(self):
        super().__init__()

    async def fetch_rss(self,
                        query: str | None = None,
                        release_groups: list[str] | None = None) -> str:
        if not query:
            query = ""
        if release_groups:
            release_groups_query = "|".join(f'"{rg}"' for rg in release_groups)
            query = f"{query} {release_groups_query}".strip()
        self.logger.debug(f"Fetching RSS for query: {query}")
        url = self.BASE_URL + self.Endpoint.RSS.format(
            query=query, category_code=RSS_CATEGORY_TO_CODE_MAP[config.user_settings.rss_category]
        )
        response = await self._request("GET", url)
        return self._process_response(response)

    async def healthcheck(self):
        url = self.BASE_URL + self.Endpoint.RSS.format(
            query="nonexistentqueryfortesting",
            category_code=RSS_CATEGORY_TO_CODE_MAP[config.user_settings.rss_category]
        )
        response = await self._request("GET", url)
        if response.status != 200:
            raise ExternalServiceException(detail="Nyaa error",
                                           status_code=response.status)

    # noinspection PyMethodMayBeStatic
    def _process_response(self, response: StandardResponse):
        if response.status >= 500:
            raise ExternalServiceException("Nyaa is down",
                                           status_code=response.status,
                                           debug_info={
                                               "url": response.url,
                                               "status": response.status,
                                               "content": response.text,
                                               "headers": response.headers
                                           })
        elif response.status != 200:
            raise ExternalServiceException(f"Unhandled response from Nyaa ({response.status}): {response.text}",
                                           status_code=response.status,
                                           debug_info={
                                               "url": response.url,
                                               "content": response.text,
                                               "headers": response.headers
                                           })

        return response.text
