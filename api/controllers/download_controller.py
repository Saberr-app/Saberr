from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Query
from fastapi.sse import EventSourceResponse, ServerSentEvent
from starlette.requests import Request

from api.controllers import minimal_polling_sse
from api.routes import api_v1_router
from components.api_components.download_api_component import DownloadAPIComponent
from api.schemas import DataEnvelope, error_responses
from api.schemas.download_schemas import (DownloadListRequest, DownloadListResponse, DownloadItem, DownloadRetryCheck,
                                          DownloadUpdatesStreamRequest, DeleteDownloadRequest)


@api_v1_router.get("/downloads", response_model=DataEnvelope[DownloadListResponse])
async def list_downloads(params: Annotated[DownloadListRequest, Query()]):
    return DataEnvelope(data=await DownloadAPIComponent().get_downloads(params=params))


@api_v1_router.get("/downloads/updates/stream", response_class=EventSourceResponse)
async def get_download_updates_stream(request: Request,
                                      params: Annotated[DownloadUpdatesStreamRequest, Query()]
                                      ) -> AsyncIterator[ServerSentEvent]:
    download_ids = set(params.download_ids)
    async for event in minimal_polling_sse(request=request,
                                           callable_=DownloadAPIComponent().get_download_updates_stream,
                                           frequency=params.freq,
                                           download_ids=download_ids,
                                           nullify_func=DownloadAPIComponent.nullify_unchanged):
        yield event
        if not download_ids:
            break


@api_v1_router.get("/downloads/{download_id}", response_model=DataEnvelope[DownloadItem],
                   responses=error_responses(404))
async def get_download(download_id: int):
    return DataEnvelope(data=await DownloadAPIComponent().get_download(download_id=download_id))


@api_v1_router.post("/downloads/{download_id}/retry", status_code=204,
                    responses=error_responses(404, 422))
async def retry_download(download_id: int):
    await DownloadAPIComponent().retry_download(download_id=download_id)


@api_v1_router.post("/downloads/{download_id}/retry/check", response_model=DataEnvelope[DownloadRetryCheck],
                    responses=error_responses(404, 422))
async def check_download_retry(download_id: int):
    return DataEnvelope(data=await DownloadAPIComponent().check_download_retry(download_id=download_id))


@api_v1_router.post("/downloads/{download_id}/delete", status_code=204,
                    responses=error_responses(404, 422, 502))
async def delete_download(download_id: int, body: DeleteDownloadRequest):
    await DownloadAPIComponent().delete_download(download_id=download_id, body=body)
