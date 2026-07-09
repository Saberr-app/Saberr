from common.exceptions import ExternalServiceException
from services import ThirdPartyService, StandardResponse


class StaticFilesService(ThirdPartyService):

    def __init__(self):
        super().__init__()

    async def get_arbitrary_file(self, url: str) -> bytes:
        self.logger.debug(f"Fetching static file: {url}")
        response = await self._request("GET", url)
        response = self._handle_response(response)
        return response.content

    def _handle_response(self, response) -> StandardResponse:
        if response.status_code != 200:
            self.logger.warning(f"Failed to fetch static file \"{response.url}\", status code: {response.status_code}")
            raise ExternalServiceException(f"Failed to fetch file, status code: {response.status_code}")
        return response
