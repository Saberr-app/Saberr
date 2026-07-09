import os
import re
import glob
import time
import logging
import datetime
from queue import SimpleQueue
from logging.handlers import QueueHandler, QueueListener, TimedRotatingFileHandler

from common.context_helpers import get_context_id

_FORMAT = "%(asctime)s [%(context_id)s] [%(name)s] %(levelname)s: %(message)s"
_RETENTION_DAYS = 14

_listener: QueueListener | None = None


class _ContextIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.context_id = get_context_id()
        return True


class _DatedFileHandler(TimedRotatingFileHandler):
    def __init__(self, logs_dir: str, stem: str, backup_count: int, encoding: str):
        self._logs_dir = logs_dir
        self._stem = stem
        super().__init__(self._current_path(), when="midnight",
                         backupCount=backup_count, encoding=encoding)

    def _current_path(self) -> str:
        return os.path.join(self._logs_dir, f"{self._stem}-{datetime.date.today():%Y-%m-%d}.log")

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None  # noqa
        self.baseFilename = os.path.abspath(self._current_path())
        if not self.delay:
            self.stream = self._open()
        self.rolloverAt = self.computeRollover(int(time.time()))
        for path in self.getFilesToDelete():
            os.remove(path)

    def getFilesToDelete(self):
        if self.backupCount <= 0:
            return []
        cutoff = datetime.date.today() - datetime.timedelta(days=self.backupCount)
        pattern = re.compile(rf"{re.escape(self._stem)}-(\d{{4}}-\d{{2}}-\d{{2}})\.log$")
        stale = []
        for path in glob.glob(os.path.join(self._logs_dir, f"{self._stem}-*.log")):
            match = pattern.search(os.path.basename(path))
            if not match:
                continue
            try:
                file_date = datetime.date.fromisoformat(match.group(1))
            except ValueError:
                continue
            if file_date < cutoff:
                stale.append(path)
        return stale


def _build_handlers(filename: str) -> list[logging.Handler]:
    logs_dir = os.path.join(os.environ["DATA_DIR"], "logs")
    os.makedirs(logs_dir, exist_ok=True)

    formatter = logging.Formatter(_FORMAT)

    file_handler = _DatedFileHandler(
        logs_dir=logs_dir,
        stem=filename.removesuffix(".log"),
        backup_count=_RETENTION_DAYS,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    return [file_handler, console_handler]


def setup_logging(filename: str = "saberr.log", async_safe: bool = True) -> None:
    global _listener

    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    root.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

    handlers = _build_handlers(filename)
    context_filter = _ContextIdFilter()

    if async_safe:
        queue: SimpleQueue = SimpleQueue()
        queue_handler = QueueHandler(queue)
        queue_handler.addFilter(context_filter)
        root.addHandler(queue_handler)

        _listener = QueueListener(queue, *handlers, respect_handler_level=True)
        _listener.start()
    else:
        for handler in handlers:
            handler.addFilter(context_filter)
            root.addHandler(handler)


def stop_logging() -> None:
    global _listener
    if _listener is not None:
        _listener.stop()
        _listener = None
