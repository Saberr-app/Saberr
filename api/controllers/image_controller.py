from starlette.responses import FileResponse, HTMLResponse

from api.routes import images_router
from api.schemas import error_responses
from common.exceptions import ExternalServiceException
from components.external_image_component import ExternalImageComponent
from config import config


@images_router.get("/{image_encoded_url_path:path}", responses=error_responses(502, 404))
async def get_proxied_image(image_encoded_url_path: str):
    if not config.proxy_external_images:
        return HTMLResponse(status_code=404)
    try:
        file_path = await ExternalImageComponent().get_file_path_for_encoded_external_image_url(image_encoded_url_path)
    except ExternalServiceException as e:
        return HTMLResponse(status_code=e.status_code)
    except Exception:
        return HTMLResponse(status_code=502)
    return FileResponse(file_path, headers={"Cache-Control": "max-age=2678400"})
