import asyncio
# noinspection PyPackageRequirements
import contextvars
import functools
import logging
import uuid
from dataclasses import dataclass
from typing import Callable, Coroutine, ParamSpec, TypeVar

_P = ParamSpec('_P')
_R = TypeVar('_R')

_context_id_var = contextvars.ContextVar('context_id', default="default-context-")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RequestMetadata:
    ip_address: str | None = None
    country: str | None = None
    browser: str | None = None


_request_metadata_var = contextvars.ContextVar('request_metadata', default=RequestMetadata())


def get_context_id() -> str:
    return _context_id_var.get()


def set_context_id(context_id: str | None = None) -> contextvars.Token:
    return _context_id_var.set(context_id or uuid.uuid4().hex[:16])


def reset_context_id(token: contextvars.Token):
    _context_id_var.reset(token)


def get_request_metadata() -> RequestMetadata:
    return _request_metadata_var.get()


def set_request_metadata(ip_address: str | None = None,
                         country: str | None = None,
                         browser: str | None = None) -> contextvars.Token:
    return _request_metadata_var.set(RequestMetadata(ip_address=ip_address, country=country, browser=browser))


def reset_request_metadata(token: contextvars.Token):
    _request_metadata_var.reset(token)


def create_isolated_task(coro: Coroutine) -> asyncio.Task:
    """
    Create an isolated task with its own context.
    Args:
        coro (Coroutine): The coroutine to run as a task.
    Returns:
        asyncio.Task: The created task.
    """
    def runner():
        async def wrapper():
            token = set_context_id()
            try:
                await coro
            except Exception as e:
                logger.error(f"Error while executing isolated task {coro.__qualname__}: {e}", exc_info=True)
            finally:
                reset_context_id(token)
        return asyncio.create_task(wrapper())

    return contextvars.copy_context().run(runner)


def create_task(coro: Coroutine) -> asyncio.Task:
    """
    Create a task with the current context.
    Args:
        coro (Coroutine): The coroutine to run as a task.
    Returns:
        asyncio.Task: The created task.
    """
    async def wrapper():
        try:
            await coro
        except Exception as e:
            logger.error(f"Error while executing task {coro.__qualname__}: {e}", exc_info=True)

    return asyncio.get_running_loop().create_task(wrapper())


async def thread_out(func: Callable[_P, _R], *args: _P.args, **kwargs: _P.kwargs) -> _R:
    """
    Run a blocking, synchronous function in a worker thread without blocking the event loop.
    The current context (including the context id) is copied into the thread.
    Args:
        func (Callable): The blocking callable to run.
        *args: Positional arguments forwarded to func.
        **kwargs: Keyword arguments forwarded to func.
    Returns:
        The return value of func.
    """
    return await asyncio.to_thread(functools.partial(func, *args, **kwargs))
