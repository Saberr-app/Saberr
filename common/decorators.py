import asyncio
import inspect
import logging
import time
from functools import wraps
from types import coroutine

from common.db import execute_post_commit_actions, execute_post_rollback_actions
from common.exceptions import (InvalidSettingValueException, InvalidReleaseGroupException, ObjectNotFoundException,
                               NotFoundException, ValidationException, ExternalServiceException,
                               WorkerAlreadyRunningException, ResourceLockedException, AnilistNotAuthenticatedException,
                               AnilistUnauthorizedException, AnilistNotFoundException, BaseSaberrException,
                               BadRequestException, BaseAPIException, FailedDependencyException)
from constants import WorkerName

logger = logging.getLogger(__name__)


def periodic_worker(frequency: int, initial_delay: int = 0, listed: bool = True):
    """
    Decorator to mark a coroutine function as a periodic worker.
    Args:
        frequency (int): Frequency of execution in seconds.
        initial_delay (int): Initial delay before the first run in seconds.
        listed (bool): Whether the worker should be listed in the get workers API.
    """
    def decorator(func):
        if not inspect.iscoroutinefunction(func):
            raise TypeError(f"Periodic worker {func.__name__} must be a coroutine function.")
        if not hasattr(WorkerName, func.__name__.upper()):
            raise ValueError(f"WorkerName enum is missing an entry for {func.__name__}.")
        func.worker_data = {
            "id": getattr(WorkerName, func.__name__.upper()).name,
            "name": getattr(WorkerName, func.__name__.upper()).value,
            "initial_delay": initial_delay,
            "frequency": frequency,
            "listed": listed
        }

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def suppress_and_log(log: bool = True, ignore_exceptions: tuple = (), default_return=None):
    """
    Decorator to catch any exceptions and log them instead of raising.
    Args:
        log: Whether to log the exception.
        ignore_exceptions: Tuple of exception types to ignore and not log.
        default_return: Value to return if an exception is caught (default is None).
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log and (not ignore_exceptions or not isinstance(e, ignore_exceptions)):
                    logger.warning(f"Suppress-and-log coroutine {func.__name__} raised an exception: {e}",
                                   exc_info=True)
                return default_return

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log and not isinstance(e, ignore_exceptions):
                    logger.warning(f"Suppress-and-log function {func.__name__} raised an exception: {e}",
                                   exc_info=True)
                return default_return

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator


def with_retry(count: int, delay: int = 1):
    """
    Decorator to retry a function or coroutine a specified number of times with a delay between attempts.
    Args:
        count (int): Number of retry attempts.
        delay (int): Delay in seconds between attempts.
    """
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                for i in range(count):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        if i == count - 1:
                            raise e
                        await asyncio.sleep(delay)
                return None
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                for i in range(count):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if i == count - 1:
                            raise e
                        time.sleep(delay)
                return None
        return wrapper
    return decorator


def require_db_session(coro: coroutine):
    @wraps(coro)
    async def wrapper(*args, **kwargs):
        from common.db import session_context, get_session
        async with session_context():
            try:
                return await coro(*args, **kwargs)
            except Exception as e:
                await get_session().rollback()
                await execute_post_rollback_actions()
                raise e
            finally:
                await get_session().commit()
                await execute_post_commit_actions()

    return wrapper


def api_component(coro: coroutine):
    # translate app exceptions to api exceptions
    @wraps(coro)
    async def wrapper(*args, **kwargs):
        try:
            return await coro(*args, **kwargs)
        except BaseAPIException:  # already an API exception - let it through with its own status
            raise
        except (InvalidSettingValueException, InvalidReleaseGroupException, AnilistNotAuthenticatedException) as e:
            raise ValidationException(e.detail) from e
        except (ObjectNotFoundException, AnilistNotFoundException) as e:
            raise NotFoundException(e.detail) from e
        except AnilistUnauthorizedException as e:
            raise FailedDependencyException(e.detail) from e
        except ExternalServiceException as e:
            raise FailedDependencyException(f"[{e.status_code}] {e.detail}") from e
        except WorkerAlreadyRunningException as e:
            raise ResourceLockedException(e.detail) from e
        except BaseSaberrException as e:  # final fallback - should narrow it down to user-readable errors in the future
            raise BadRequestException(e.detail) from e

    return wrapper
