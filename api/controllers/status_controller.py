from collections.abc import AsyncIterator

from fastapi.sse import EventSourceResponse, ServerSentEvent
from starlette.requests import Request

from api.controllers import minimal_polling_sse
from api.routes import api_v1_router
from components.api_components.status_api_component import StatusAPIComponent
from api.schemas import DataEnvelope
from api.schemas.status_schemas import Status


@api_v1_router.get("/status", response_model=DataEnvelope[Status],  response_model_exclude_unset=True)
async def get_status():
    return DataEnvelope(data=await StatusAPIComponent().get_status())


@api_v1_router.get("/status/stream", response_class=EventSourceResponse)
async def get_status_stream(request: Request, freq: int = 3) -> AsyncIterator[ServerSentEvent]:
    async for event in minimal_polling_sse(request=request,
                                           callable_=StatusAPIComponent().get_status_stream_data,
                                           frequency=freq):
        yield event
