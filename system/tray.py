import logging
import os
import sys
import time
import ctypes
import socket
import threading
import subprocess

from system import WINDOWS_SHUTDOWN_EVENT_NAME, WINDOWS_BACKEND_SHUTDOWN_EVENT_NAME
from system.on_start import load_env_overrides, prep_data_dir, load_context_specific_env

_APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
_ROOT_DIR = os.path.dirname(_APP_DIR)
_MARIADB_BIN = os.path.join(_ROOT_DIR, "mariadb", "bin")
_MARIADBD = os.path.join(_MARIADB_BIN, "mariadbd.exe")
_MARIADB_INSTALL_DB = os.path.join(_MARIADB_BIN, "mariadb-install-db.exe")
_MARIADB_DEFAULTS = os.path.join(_ROOT_DIR, "mariadb", "my.ini")
_PREFERRED_DB_PORT = 5798
_DB_ROOT_PASSWORD = "root"

_MUTEX_NAME = "Global\\SaberrTray"
_ERROR_ALREADY_EXISTS = 183
_logger = logging.getLogger(__name__)


_MB_ICONERROR = 0x10
_MB_ICONINFORMATION = 0x40
_MB_SETFOREGROUND = 0x10000


def _show_dialog(message: str, title: str = "Saberr", icon: int = _MB_ICONERROR) -> None:
    ctypes.windll.user32.MessageBoxW(None, message, title, icon | _MB_SETFOREGROUND)


def _acquire_single_instance():
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if not handle or ctypes.windll.kernel32.GetLastError() == _ERROR_ALREADY_EXISTS:
        return None
    return handle


def signal_shutdown() -> None:
    """Set the named event the running tray waits on, triggering a graceful teardown"""
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateEventW.restype = ctypes.c_void_p
    handle = kernel32.CreateEventW(None, True, False, WINDOWS_SHUTDOWN_EVENT_NAME)
    if handle:
        kernel32.SetEvent(ctypes.c_void_p(handle))


def _signal_backend_shutdown() -> None:
    """Ask the backend to shut down gracefully"""
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateEventW.restype = ctypes.c_void_p
    handle = kernel32.CreateEventW(None, False, False, WINDOWS_BACKEND_SHUTDOWN_EVENT_NAME)
    if handle:
        kernel32.SetEvent(ctypes.c_void_p(handle))


def _wait_for_shutdown_signal(on_signal) -> None:
    """Block until the backend child relays a shutdown via the named event, then run on_signal"""
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateEventW.restype = ctypes.c_void_p
    handle = kernel32.CreateEventW(None, True, False, WINDOWS_SHUTDOWN_EVENT_NAME)
    if not handle:
        return
    kernel32.WaitForSingleObject(ctypes.c_void_p(handle), 0xFFFFFFFF)
    _logger.info("Received shutdown signal from backend")
    on_signal()


def _free_port(preferred: int) -> int:
    for port in (preferred, *range(preferred + 1, preferred + 50)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    port_error = (f"No free DB port found in range {preferred}-{preferred + 49}; Either free a port "
                  f"or change the config/params to use a different port.")
    _logger.error(port_error)
    raise RuntimeError(port_error)


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        return probe.connect_ex(("127.0.0.1", port)) == 0


def _reclaim_stale_db() -> None:
    import pymysql
    if not _port_in_use(_PREFERRED_DB_PORT):
        return
    try:
        connection = pymysql.connect(host="127.0.0.1", port=_PREFERRED_DB_PORT, user="root",
                                     password=_DB_ROOT_PASSWORD, connect_timeout=2)
    except pymysql.err.OperationalError:
        return  # not our DB (or something else on the port) — leave it; _free_port will skip past it
    _logger.warning("Found a leftover MariaDB on the preferred port; shutting it down to reclaim the data dir")
    try:
        connection.cursor().execute("SHUTDOWN")
    except pymysql.err.OperationalError:
        pass
    deadline = time.time() + 15
    while time.time() < deadline and _port_in_use(_PREFERRED_DB_PORT):
        time.sleep(0.5)


def _wait_for_db(port: int, process: subprocess.Popen, timeout: int = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"MariaDB exited during startup (exit code {process.returncode}). "
                               f"Another mariadbd is likely still using the data directory.")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.5)
    raise RuntimeError("MariaDB did not become ready in time")


class Supervisor:
    def __init__(self):
        self.data_dir = os.environ["DATA_DIR"]
        self.db_data_dir = os.path.join(self.data_dir, "db")
        _reclaim_stale_db()
        self.db_port = _free_port(_PREFERRED_DB_PORT)
        self.web_port = int(os.environ.get("PORT", "8125"))
        self.db_process = None
        self.backend_process = None
        self._stop = threading.Event()
        self._db_lock = threading.Lock()
        self._db_action = threading.Lock()
        self._backend_action = threading.Lock()

    def _ensure_db_initialized(self) -> None:
        if not os.path.isdir(self.db_data_dir) or not os.listdir(self.db_data_dir):
            _logger.info(f"Initializing MariaDB data directory at {self.db_data_dir}")
            os.makedirs(self.db_data_dir, exist_ok=True)
            subprocess.run([_MARIADB_INSTALL_DB, f"--config={_MARIADB_DEFAULTS}",
                            f"--datadir={self.db_data_dir}",
                            f"--password={_DB_ROOT_PASSWORD}"], check=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)

    def _start_db(self) -> None:
        _logger.info(f"Starting MariaDB on port {self.db_port}")
        self.db_process = subprocess.Popen([
            _MARIADBD,
            f"--defaults-file={_MARIADB_DEFAULTS}",
            f"--datadir={self.db_data_dir}",
            f"--port={self.db_port}",
            "--bind-address=127.0.0.1",
        ], creationflags=subprocess.CREATE_NO_WINDOW)
        _wait_for_db(self.db_port, self.db_process)
        _logger.debug(f"MariaDB is ready on port {self.db_port}")

    def _provision_db(self) -> None:
        import pymysql

        db_name = os.environ["DB_NAME"]
        db_user = os.environ["DB_USER"]
        db_password = os.environ["DB_PASSWORD"]

        _logger.debug(f"Provisioning database '{db_name}' and user '{db_user}'")
        connection = pymysql.connect(host="127.0.0.1", port=self.db_port, user="root",
                                     password=_DB_ROOT_PASSWORD)
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` COLLATE utf8mb4_general_ci")
                cursor.execute("CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s", (db_user, db_password))
                cursor.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO %s@'%%'", (db_user,))
                cursor.execute("FLUSH PRIVILEGES")
            connection.commit()
        finally:
            connection.close()

    def _start_backend(self) -> None:
        if _port_in_use(self.web_port):
            port_error = (f"Port {self.web_port} is already in use; Either free the port "
                          f"or change the config/params to use a different port.")
            _logger.error(port_error)
            raise RuntimeError(port_error)
        command = [sys.executable]
        if "__compiled__" not in globals():
            command.append("main.py")
        command += [
            "--app",
            "--DATA-DIR", self.data_dir,
            "--WEB-DIR", os.environ["WEB_DIR"],
            "--DB-PORT", str(self.db_port),
        ]
        if os.environ.get("PORT"):
            command += ["--PORT", os.environ["PORT"]]
        if os.environ.get("LOG_LEVEL"):
            command += ["--LOG-LEVEL", os.environ["LOG_LEVEL"]]
        self.backend_process = subprocess.Popen(command, cwd=_APP_DIR,
                                                creationflags=subprocess.CREATE_NO_WINDOW)
        _logger.info(f"Backend process started (pid {self.backend_process.pid})")

    def _stop_db(self) -> None:
        if not self.db_process or self.db_process.poll() is not None:
            return
        import pymysql
        try:
            connection = pymysql.connect(host="127.0.0.1", port=self.db_port, user="root",
                                         password=_DB_ROOT_PASSWORD)
            connection.cursor().execute("SHUTDOWN")
        except pymysql.err.OperationalError:
            _logger.warning("Failed to send SHUTDOWN to MariaDB; it may not stop cleanly")
        try:
            self.db_process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            _logger.warning("MariaDB did not exit after SHUTDOWN; killing")
            self.db_process.kill()

    def _stop_backend(self) -> None:
        if not self.backend_process or self.backend_process.poll() is not None:
            return
        _logger.info("Requesting graceful backend shutdown")
        _signal_backend_shutdown()
        try:
            self.backend_process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            _logger.warning("Backend did not exit gracefully; terminating")
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                _logger.warning("Backend did not exit after terminate; killing")
                self.backend_process.kill()

    def is_db_running(self) -> bool:
        return self.db_process is not None and self.db_process.poll() is None

    def is_backend_running(self) -> bool:
        return self.backend_process is not None and self.backend_process.poll() is None

    def start(self) -> None:
        with self._db_action, self._backend_action:
            try:
                self._ensure_db_initialized()
                with self._db_lock:
                    self._start_db()
                self._provision_db()
                self._start_backend()
            except Exception:
                self.stop()  # don't leave an orphaned mariadbd holding the datadir lock
                raise

    def restart_db(self) -> None:
        if not self._db_action.acquire(blocking=False):
            _logger.info("A database start/restart is already in progress; ignoring")
            return
        try:
            _logger.info("Restarting database service")
            with self._db_lock:
                self._stop_db()
                self._start_db()
        finally:
            self._db_action.release()

    def restart_backend(self) -> None:
        if not self._backend_action.acquire(blocking=False):
            _logger.info("A backend start/restart is already in progress; ignoring")
            return
        try:
            _logger.info("Restarting Saberr service")
            self._stop_backend()
            self._start_backend()
        finally:
            self._backend_action.release()

    def monitor(self) -> None:
        while not self._stop.wait(2):
            with self._db_lock:
                if not self._stop.is_set() and self.db_process.poll() is not None:
                    _logger.warning("MariaDB process exited unexpectedly; restarting")
                    self._start_db()

    def stop(self) -> None:
        _logger.info("Stopping Saberr supervisor")
        self._stop.set()
        self._stop_backend()
        with self._db_lock:
            self._stop_db()


def run_tray() -> None:
    instance_handle = _acquire_single_instance()
    if instance_handle is None:
        _show_dialog("Saberr is already running.", icon=_MB_ICONINFORMATION)
        return

    import pystray
    from PIL import Image

    os.chdir(_APP_DIR)
    load_env_overrides()
    from common.logging_config import setup_logging
    setup_logging("tray.log", async_safe=False)
    prep_data_dir()
    load_context_specific_env()

    try:
        supervisor = Supervisor()
    except Exception as exc:
        _logger.exception("Failed to initialize Saberr supervisor")
        _show_dialog(f"Saberr failed to start:\n\n{exc}\n\nSee the logs in the data folder for details.")
        raise SystemExit(1)

    def on_open(_icon, _item):
        os.startfile(f"http://127.0.0.1:{supervisor.web_port}")

    def on_open_logs(_icon, _item):
        os.startfile(os.path.join(supervisor.data_dir, "logs"))

    def on_quit(_icon, _item):
        supervisor.stop()
        _icon.stop()

    def _run_service_action(label, action):
        def task():
            try:
                action()
            except Exception as action_exc:
                _logger.exception(f"Failed to {label}")
                _show_dialog(f"Failed to {label}:\n\n{action_exc}")
            icon.update_menu()
        threading.Thread(target=task, daemon=True).start()

    def _service_submenu(name, port_getter, running_getter, action):
        return pystray.MenuItem(
            lambda _item: f"{name} ({'Started' if running_getter() else 'Stopped'})",
            pystray.Menu(
                pystray.MenuItem(lambda _item: f"Port: {port_getter()}", None, enabled=False),
                pystray.MenuItem(
                    lambda _item: "Restart" if running_getter() else "Start",
                    lambda _icon, _item: _run_service_action(
                        f"restart {name.lower()}" if running_getter() else f"start {name.lower()}",
                        action),
                ),
            ),
        )

    icon = pystray.Icon(
        "Saberr",
        Image.open(os.path.join(_APP_DIR, "assets", "icon.png")),
        menu=pystray.Menu(
            pystray.MenuItem("Open Saberr", on_open),
            pystray.Menu.SEPARATOR,
            _service_submenu("Saberr service", lambda: supervisor.web_port,
                             supervisor.is_backend_running, supervisor.restart_backend),
            _service_submenu("Database service", lambda: supervisor.db_port,
                             supervisor.is_db_running, supervisor.restart_db),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Logs", on_open_logs),
            pystray.MenuItem("Quit", on_quit),
        ),
    )

    def _open_when_ready():
        deadline = time.time() + 30
        while time.time() < deadline and not _port_in_use(supervisor.web_port):
            time.sleep(0.5)
        on_open(icon, None)

    def _startup(_icon):
        # runs on pystray's setup thread; with setup= the icon isn't shown unless we make it visible
        _icon.visible = True
        try:
            supervisor.start()
        except Exception as start_exc:
            _logger.exception("Failed to start Saberr supervisor")
            _show_dialog(f"Saberr failed to start:\n\n{start_exc}\n\nSee the logs in the data folder for details.")
            _icon.stop()
            return
        _logger.info(f"Saberr tray started; web UI on port {supervisor.web_port}")
        _icon.update_menu()
        threading.Thread(target=supervisor.monitor, daemon=True).start()
        threading.Thread(target=_open_when_ready, daemon=True).start()
        threading.Thread(target=_wait_for_shutdown_signal,
                         args=(lambda: on_quit(icon, None),), daemon=True).start()

    icon.run(setup=_startup)
