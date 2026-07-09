import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def create_app():
    from api.middleware.auth_middleware import AuthMiddleware
    from api.middleware.db_session_middleware import DBSessionMiddleware
    from api.middleware.response_middleware import ResponseMiddleware
    from api.middleware.context_middleware import ContextMiddleware
    from api.routes import register_routes
    from app_state import anime_relations, worker_manager
    from config import config
    from components.audit_log_component import AuditLogComponent
    from system.on_shutdown import on_shutdown_actions

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        logger.info("Starting up application...")
        audit_log_component = AuditLogComponent()
        await audit_log_component.log_app_started(config.app_version.original_version_string)
        await anime_relations.load_relations()
        await worker_manager.run()
        yield
        logger.info("shutting down application...")
        await audit_log_component.log_app_exiting()
        await worker_manager.stop()
        await on_shutdown_actions()

    app = FastAPI(title="Saberr",
                  lifespan=lifespan,
                  debug=config.debug,
                  version=config.app_version.original_version_string,
                  docs_url="/docs" if config.debug else None,
                  redoc_url="/redoc" if config.debug else None,
                  openapi_url="/openapi.json" if config.debug else None)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(DBSessionMiddleware)
    app.add_middleware(ResponseMiddleware)
    app.add_middleware(ContextMiddleware)
    use_wildcard_origin = not config.user_settings.published_url or config.allow_all_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if use_wildcard_origin else [config.user_settings.published_url],
        allow_credentials=not use_wildcard_origin,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_routes(app)

    return app
