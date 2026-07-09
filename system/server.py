from datetime import datetime, UTC

import ctypes
import threading
from system import WINDOWS_BACKEND_SHUTDOWN_EVENT_NAME, shutdown_event
import uvicorn

_server: uvicorn.Server | None = None
up_since: datetime | None = None


class Server(uvicorn.Server):
    def __init__(self, config: uvicorn.Config):
        super().__init__(config)
        global _server
        _server = self

    def handle_exit(self, *args, **kwargs):
        shutdown_event.set()
        super().handle_exit(*args, **kwargs)

    async def serve(self, *args, **kwargs):
        global up_since
        up_since = datetime.now(UTC)
        self._watch_for_tray_shutdown()
        await super().serve(*args, **kwargs)
    
    @staticmethod
    def _watch_for_tray_shutdown():
        # windows context only: lets the tray request a graceful backend shutdown via a named event
        from config import config
        from constants import AppContext
        if config.context != AppContext.WINDOWS:
            return

        def _wait():
            kernel32 = ctypes.windll.kernel32
            kernel32.CreateEventW.restype = ctypes.c_void_p
            handle = kernel32.CreateEventW(None, False, False, WINDOWS_BACKEND_SHUTDOWN_EVENT_NAME)
            if not handle:
                return
            kernel32.WaitForSingleObject(ctypes.c_void_p(handle), 0xFFFFFFFF)
            _trigger_graceful_exit()

        threading.Thread(target=_wait, daemon=True).start()


def _trigger_graceful_exit():
    """Ask uvicorn to shut down gracefully (runs lifespan shutdown → audit log + cleanup)."""
    shutdown_event.set()
    if _server is not None:
        _server.should_exit = True


def request_shutdown():
    _trigger_graceful_exit()
    _signal_tray_shutdown()


def _signal_tray_shutdown():
    from config import config
    from constants import AppContext
    if config.context != AppContext.WINDOWS:
        return
    import ctypes
    from system import WINDOWS_SHUTDOWN_EVENT_NAME
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateEventW.restype = ctypes.c_void_p
    handle = kernel32.CreateEventW(None, True, False, WINDOWS_SHUTDOWN_EVENT_NAME)
    if handle:
        kernel32.SetEvent(ctypes.c_void_p(handle))


def get_up_since() -> datetime:
    return up_since
