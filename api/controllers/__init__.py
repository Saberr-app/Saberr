import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Callable

from fastapi.sse import ServerSentEvent
from starlette.requests import Request

from common.exceptions import BaseAPIException
from system import shutdown_event


logger = logging.getLogger("SSE")


def _nullify_unchanged(previous_status, current_status):
    if previous_status is None:
        return
    for field in current_status.model_fields:
        if getattr(previous_status, field) == getattr(current_status, field):
            setattr(current_status, field, None)


async def minimal_polling_sse(request: Request,
                              callable_: Callable,
                              frequency: int,
                              nullify_func: Callable = _nullify_unchanged,
                              **kwargs) -> AsyncIterator[ServerSentEvent]:
    if frequency < 1:
        frequency = 1
    ref, previous_status = 1, None
    while not shutdown_event.is_set() and not await request.is_disconnected():
        try:
            current_status = await callable_(ref, **kwargs)
        except BaseAPIException as e:
            # response middleware normally intercepts this exception and returns it to the client with the
            # appropriate status code, can't be achieved with streams therefore cleanly exit to avoid error logs
            logger.debug(f"API exception while polling SSE: {e} ({e.code} - {e.detail})")
            break
        new_status = current_status.model_copy()
        nullify_func(previous_status, current_status)
        previous_status = new_status
        yield ServerSentEvent(raw_data=current_status.model_dump_json(exclude_none=True))
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=frequency)
            break
        except asyncio.TimeoutError:
            pass
        ref += 1
