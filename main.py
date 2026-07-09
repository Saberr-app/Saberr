__all__ = []

import asyncio
import logging

import uvicorn


_logger = logging.getLogger(__name__)


async def serve():
    from system.server import Server
    from app import create_app
    from config import config
    _logger.info(f"Site will serve on http://localhost:{config.port}")

    uvicorn_config = uvicorn.Config(
        create_app(),
        host="0.0.0.0",
        port=config.port,
        log_level=config.log_level,
        log_config=None,
        access_log=False,
        timeout_graceful_shutdown=5,
    )

    server = Server(uvicorn_config)
    await server.serve()


if __name__ == "__main__":
    import sys
    from constants import AppContext
    from system.on_start import resolve_context

    if "--quit" in sys.argv:
        from system.tray import signal_shutdown
        signal_shutdown()
        sys.exit(0)

    run_as_tray = "--tray" in sys.argv or (
        "--app" not in sys.argv and resolve_context() == AppContext.WINDOWS.value
    )

    if run_as_tray:
        from system.tray import run_tray
        run_tray()
    else:
        from system.on_start import on_start_actions
        on_start_actions()
        try:
            asyncio.run(serve())
        except KeyboardInterrupt:
            pass
