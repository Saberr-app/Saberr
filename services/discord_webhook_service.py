import json

import aiohttp

from common.exceptions import ExternalServiceException
from config import config
from services import ThirdPartyService


class DiscordWebhookService(ThirdPartyService):

    def __init__(self):
        super().__init__()

    @property
    def notifications_discord_webhook_url(self) -> str | None:
        return config.user_settings.notifications_discord_webhook_url

    @property
    def webhook_username(self):
        return config.user_settings.discord_webhook_username

    @property
    def webhook_avatar_image(self) -> str | None:
        return config.user_settings.discord_webhook_avatar_url

    async def send_notification(self, payload: dict, author_png_image: bytes = None):
        if not self.notifications_discord_webhook_url:
            self.logger.warning("No Discord webhook URL configured for general notifications")
            return
        await self.send_message(webhook_url=self.notifications_discord_webhook_url,
                                payload=payload,
                                author_png_image=author_png_image)

    async def send_message(self, webhook_url: str, payload: dict, author_png_image: bytes = None):
        self.logger.debug(f"Executing Discord webhook: {webhook_url} | {payload}")
        if not payload.get("username") and self.webhook_username:
            payload["username"] = self.webhook_username
        if not payload.get("avatar_url") and self.webhook_avatar_image:
            payload["avatar_url"] = self.webhook_avatar_image
        if author_png_image:
            payload["embeds"][0]["author"]["icon_url"] = "attachment://author.png"
            form = aiohttp.FormData()
            form.add_field(
                "payload_json",
                json.dumps(payload),
            )
            form.add_field(
                "file",
                author_png_image,
                filename="author.png",
                content_type="image/png"
            )
            response = await self._request("POST", webhook_url, data=form)
        else:
            response = await self._request("POST", webhook_url, json_=payload)
        if response.status not in range(200, 300):
            self.logger.debug(f"Failed to send Discord webhook: {response.status} | {response.text}")
            raise ExternalServiceException(f"Discord webhook error: {response.status}")

    async def healthcheck(self, webhook_url: str):
        response = await self._request("GET", webhook_url)
        if response.status_code not in range(200, 300):
            if response.status_code in range(400, 500):
                try:
                    error_message = response.json.get("message", "No error message")
                except:
                    error_message = f"Non-JSON response: {response.text}"
            else:
                error_message = f"Discord is currently unavailable"
            raise ExternalServiceException(detail=error_message,
                                           status_code=response.status_code)
