from api.routes import api_v1_router
from components.api_components.tracked_anime_api_component import TrackedAnimeAPIComponent
from constants import TrackedAnimeStatus
from api.schemas import DataEnvelope, error_responses
from api.schemas.tracked_anime_schemas import (TrackedAnimeCreateRequest, TrackedAnimeItem,
                                               TrackedAnimeUpdateRequest, TrackedAnimeListResponse,
                                               TrackedAnimeBatchArchiveRequest,
                                               TrackedAnimeBatchDeleteRequest, TrackedAnimeItemWithEpisodes,
                                               TrackedAnimeItemEpisodeList, TrackedAnimeItemEpisodeDetails,
                                               TrackedAnimeEpisodeUpdateRequest)


@api_v1_router.post("/tracked-anime", status_code=204,
                    responses=error_responses(422, 502))
async def create_tracked_anime(body: TrackedAnimeCreateRequest):
    await TrackedAnimeAPIComponent().create_tracked_anime(body=body)


@api_v1_router.get("/tracked-anime", response_model=DataEnvelope[TrackedAnimeListResponse])
async def get_tracked_anime_list(force_freshness: bool = False,
                                 status: TrackedAnimeStatus = TrackedAnimeStatus.ACTIVE,
                                 anilist_id: int = None):
    return DataEnvelope(data=await TrackedAnimeAPIComponent().get_tracked_anime_list(
        force_freshness=force_freshness, status=status, anilist_id=anilist_id))


@api_v1_router.post("/tracked-anime/batch-archive", status_code=204,
                    responses=error_responses(404))
async def batch_archive_tracked_anime(body: TrackedAnimeBatchArchiveRequest):
    await TrackedAnimeAPIComponent().batch_archive_tracked_anime(body=body)


@api_v1_router.post("/tracked-anime/batch-delete", status_code=204,
                    responses=error_responses(404))
async def batch_delete_tracked_anime(body: TrackedAnimeBatchDeleteRequest):
    await TrackedAnimeAPIComponent().batch_delete_tracked_anime(body=body)


@api_v1_router.get("/tracked-anime/{tracked_anime_id}", response_model=DataEnvelope[TrackedAnimeItemWithEpisodes],
                   responses=error_responses(404))
async def get_tracked_anime(tracked_anime_id: int, force_freshness: bool = False, with_episodes: bool = True):
    return DataEnvelope(data=await TrackedAnimeAPIComponent().get_tracked_anime(
        tracked_anime_id=tracked_anime_id, force_freshness=force_freshness, with_episodes=with_episodes
    ))


@api_v1_router.put("/tracked-anime/{tracked_anime_id}", response_model=DataEnvelope[TrackedAnimeItem],
                   responses=error_responses(422, 404))
async def update_tracked_anime(tracked_anime_id: int, body: TrackedAnimeUpdateRequest):
    return DataEnvelope(data=await TrackedAnimeAPIComponent().update_tracked_anime(tracked_anime_id=tracked_anime_id,
                                                                                   body=body))


@api_v1_router.delete("/tracked-anime/{tracked_anime_id}", status_code=204,
                      responses=error_responses(404))
async def delete_tracked_anime(tracked_anime_id: int):
    await TrackedAnimeAPIComponent().delete_tracked_anime(tracked_anime_id=tracked_anime_id)


@api_v1_router.post("/tracked-anime/{tracked_anime_id}/archive", status_code=204,
                    responses=error_responses(404))
async def archive_tracked_anime(tracked_anime_id: int):
    await TrackedAnimeAPIComponent().archive_tracked_anime(tracked_anime_id=tracked_anime_id)


@api_v1_router.post("/tracked-anime/{tracked_anime_id}/unarchive", status_code=204,
                    responses=error_responses(404))
async def unarchive_tracked_anime(tracked_anime_id: int):
    await TrackedAnimeAPIComponent().unarchive_tracked_anime(tracked_anime_id=tracked_anime_id)


@api_v1_router.get("/tracked-anime/{tracked_anime_id}/episodes",
                   response_model=DataEnvelope[TrackedAnimeItemEpisodeList],
                   responses=error_responses(404))
async def get_tracked_anime_episodes(tracked_anime_id: int, offset: int, limit: int, force_freshness: bool = False):
    return DataEnvelope(data=await TrackedAnimeAPIComponent().get_tracked_anime_episodes(
        tracked_anime_id=tracked_anime_id, offset=offset, limit=limit, force_freshness=force_freshness))


@api_v1_router.get("/tracked-anime/{tracked_anime_id}/episodes/{episode_number}",
                   response_model=DataEnvelope[TrackedAnimeItemEpisodeDetails],
                   responses=error_responses(404))
async def get_tracked_anime_episode(tracked_anime_id: int,
                                    episode_number: int,
                                    force_freshness: bool = False):
    return DataEnvelope(data=await TrackedAnimeAPIComponent().get_tracked_anime_episode_details(
        tracked_anime_id=tracked_anime_id, episode_number=episode_number, force_freshness=force_freshness))


@api_v1_router.put("/tracked-anime/{tracked_anime_id}/episodes/{episode_number}",
                   status_code=204,
                   responses=error_responses(404))
async def update_tracked_anime_episode(tracked_anime_id: int,
                                       episode_number: int,
                                       data: TrackedAnimeEpisodeUpdateRequest):
    await TrackedAnimeAPIComponent().update_tracked_anime_episode(tracked_anime_id=tracked_anime_id,
                                                                  episode_number=episode_number,
                                                                  data=data)
