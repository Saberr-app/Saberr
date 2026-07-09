from common.exceptions import ExternalServiceException
from services import ThirdPartyService


class GitHubService(ThirdPartyService):
    BASE_URL = "https://api.github.com/repos/saberr-app/saberr"

    class Endpoint:
        LATEST_RELEASE = "/releases/latest"
        RELEASE_BY_TAG = "/releases/tags/{tag}"

    async def get_latest_release(self) -> dict:
        response = await self._request("GET", self.BASE_URL + self.Endpoint.LATEST_RELEASE)
        if response.status_code == 404:
            raise ExternalServiceException("Latest release not found", status_code=response.status_code)
        return response.json

    async def get_release(self, tag: str) -> dict:
        response = await self._request("GET", self.BASE_URL + self.Endpoint.RELEASE_BY_TAG.format(tag=tag))
        if response.status_code == 404:
            raise ExternalServiceException("Release not found", status_code=response.status_code)
        return response.json
