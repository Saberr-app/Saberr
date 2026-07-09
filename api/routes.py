from fastapi import APIRouter, FastAPI

api_v1_router = APIRouter(prefix="/api/v1", tags=["api"])
images_router = APIRouter(prefix="/images", tags=["images"])
web_router = APIRouter(prefix="", tags=["web"])


def register_routes(app: FastAPI) -> None:
    import api.controllers.anime_controller  # noqa: F401
    import api.controllers.audit_log_controller  # noqa: F401
    import api.controllers.download_controller  # noqa: F401
    import api.controllers.healthcheck_controller  # noqa: F401
    import api.controllers.image_controller  # noqa: F401
    import api.controllers.login_controller  # noqa: F401
    import api.controllers.mapping_controller  # noqa: F401
    import api.controllers.notification_controller  # noqa: F401
    import api.controllers.schedule_controller  # noqa: F401
    import api.controllers.settings_controller  # noqa: F401
    import api.controllers.search_controller  # noqa: F401
    import api.controllers.status_controller  # noqa: F401
    import api.controllers.system_controller  # noqa: F401
    import api.controllers.torrent_controller  # noqa: F401
    import api.controllers.tracked_anime_controller  # noqa: F401
    import api.controllers.user_anime_list_controller  # noqa: F401
    import api.controllers.web_controller  # noqa: F401

    app.include_router(api_v1_router)
    app.include_router(images_router)
    app.include_router(web_router)
