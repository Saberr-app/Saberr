import logging

from starlette.middleware.base import BaseHTTPMiddleware

from common.context_helpers import set_context_id, reset_context_id, set_request_metadata, reset_request_metadata
from utils.helpers.user_agent_helpers import format_client_descriptor

_logger = logging.getLogger("APIService")


class ContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        status_code = 500
        ip_address, country, browser = None, None, None
        try:
            ip_address = request.headers.get("cf-connecting-ip") or (request.client.host if request.client else None)
            country = request.headers.get("cf-ipcountry")
            browser = format_client_descriptor(
                sec_ch_ua=request.headers.get("sec-ch-ua"),
                sec_ch_ua_platform=request.headers.get("sec-ch-ua-platform"),
                user_agent=request.headers.get("user-agent"),
            )
        except Exception as e:
            _logger.info(f"Error parsing user agent: {e}")

        context_token = set_context_id()
        metadata_token = set_request_metadata(ip_address=ip_address, country=country, browser=browser)
        try:
            response = await call_next(request)
            status_code = response.status_code
        finally:
            _logger.debug("%s %s -> %s", request.method, request.url.path, status_code,
                          extra={"ip_address": ip_address, "country": country,
                                 "browser": browser, "user_agent": browser})
            reset_context_id(context_token)
            reset_request_metadata(metadata_token)
        return response
