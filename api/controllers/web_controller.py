import os

from starlette.responses import FileResponse, HTMLResponse

from api.routes import web_router
from config import config


@web_router.get("/{file_path:path}")
async def serve_web(file_path: str):
    if file_path == "api" or file_path == "images" or file_path.startswith(("api/", "images/")):
        return HTMLResponse(status_code=404)

    web_dir = os.path.realpath(config.web_dir)
    candidate = os.path.realpath(os.path.join(web_dir, file_path))
    if candidate != web_dir and not candidate.startswith(web_dir + os.sep):
        return HTMLResponse(status_code=404)

    if os.path.isfile(candidate):
        return FileResponse(candidate)

    if os.path.isfile(index_path := os.path.join(web_dir, "index.html")):
        return FileResponse(index_path, headers={"Cache-Control": "no-cache"})

    return HTMLResponse(status_code=404)
