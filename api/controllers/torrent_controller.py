from collections.abc import AsyncIterator

from fastapi.sse import EventSourceResponse, ServerSentEvent
from starlette.requests import Request

from api.controllers import minimal_polling_sse
from api.routes import api_v1_router
from components.api_components.torrent_api_component import TorrentAPIComponent
from api.schemas import DataEnvelope, error_responses
from api.schemas.torrent_schemas import (TorrentSearchRequest, TorrentDiscardRequest, TorrentDownloadRequest,
                                         TorrentListResponse, TorrentPullStatus, TorrentDownloadResponse,
                                         TorrentOverrideRequest, TorrentOverrideResponse)


@api_v1_router.get("/torrents", response_model=DataEnvelope[TorrentListResponse],
                   responses=error_responses(502))
async def get_torrents():
    return DataEnvelope(data=await TorrentAPIComponent().get_torrents())


@api_v1_router.get("/torrents/pull-status", response_model=DataEnvelope[TorrentPullStatus])
async def get_torrents_pull_status():
    return DataEnvelope(data=await TorrentAPIComponent().get_torrents_pull_status())


@api_v1_router.get("/torrents/pull-status/stream", response_class=EventSourceResponse)
async def get_torrents_pull_status_stream(request: Request, freq: int = 3) -> AsyncIterator[ServerSentEvent]:
    async for event in minimal_polling_sse(request=request,
                                           callable_=TorrentAPIComponent().get_torrents_pull_status,
                                           frequency=freq):
        yield event


@api_v1_router.post("/torrents/search", response_model=DataEnvelope[TorrentListResponse],
                    responses=error_responses(422, 502))
async def search_torrents(body: TorrentSearchRequest):
    return DataEnvelope(data=await TorrentAPIComponent().search_torrents(body=body))


@api_v1_router.post("/torrents/discard", status_code=204,
                    responses=error_responses(422))
async def discard_torrents(body: TorrentDiscardRequest):
    await TorrentAPIComponent().discard_torrents(body=body)


@api_v1_router.post("/torrents/download", response_model=DataEnvelope[TorrentDownloadResponse],
                    responses=error_responses(422))
async def download_torrent(body: TorrentDownloadRequest):
    return DataEnvelope(data=await TorrentAPIComponent().download_torrent(body=body))


@api_v1_router.post("/torrents/{torrent_id}/override", response_model=DataEnvelope[TorrentOverrideResponse],
                    responses=error_responses(422, 404))
async def override_torrent(torrent_id: int, body: TorrentOverrideRequest):
    return DataEnvelope(data=await TorrentAPIComponent().override_torrent(torrent_id=torrent_id, body=body))
