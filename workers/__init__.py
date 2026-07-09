import logging


class BaseWorkerClass:
    NAME = "Other tasks"

    def __init__(self):
        self._logger = logging.getLogger(self.NAME)
