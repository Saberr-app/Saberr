import asyncio
from pathlib import Path

UNSET = object()
shutdown_event = asyncio.Event()
WINDOWS_SHUTDOWN_EVENT_NAME = r"Global\SaberrShutdown"           # backend -> tray (relay web-UI shutdown)
WINDOWS_BACKEND_SHUTDOWN_EVENT_NAME = r"Global\SaberrBackendShutdown"  # tray -> backend (graceful stop)
