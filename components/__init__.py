import logging


class BaseComponent:

    def __new__(cls, *args, **kwargs):
        if cls is BaseComponent:
            raise TypeError("BaseComponent is an abstract class and cannot be instantiated directly.")
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)
