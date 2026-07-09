from typing import Annotated

from fastapi import Query

from api.routes import api_v1_router
from components.api_components.user_anime_list_api_component import UserAnimeListAPIComponent
from api.schemas import DataEnvelope, error_responses
from api.schemas.user_anime_list_schemas import (UserAnimeListRequest, UserAnimeListResponse,
                                                 UserAnimeUpdateRequest, UserAnimeUpdateResponse,
                                                 UserAnimeBatchUpdateRequest, UserAnimeBatchUpdateResponse,
                                                 UserAnimeBatchDeleteRequest, UserAnimeListItem)


@api_v1_router.get("/anime-list", response_model=DataEnvelope[UserAnimeListResponse],
                   responses=error_responses(502, 422))
async def get_anime_list(params: Annotated[UserAnimeListRequest, Query()]):
    return DataEnvelope(data=await UserAnimeListAPIComponent().get_anime_list(params=params))


@api_v1_router.post("/anime-list/batch-update", response_model=DataEnvelope[UserAnimeBatchUpdateResponse],
                    responses=error_responses(422, 502, 404))
async def batch_update_anime_list_entries(body: UserAnimeBatchUpdateRequest):
    return DataEnvelope(data=await UserAnimeListAPIComponent().batch_update_anime_list_entries(body=body))


@api_v1_router.post("/anime-list/batch-delete", status_code=204,
                    responses=error_responses(422, 502, 404))
async def batch_delete_anime_list_entries(body: UserAnimeBatchDeleteRequest):
    return DataEnvelope(data=await UserAnimeListAPIComponent().batch_delete_anime_list_entries(body=body))


@api_v1_router.get("/anime-list/{anilist_id}", response_model=DataEnvelope[UserAnimeListItem],
                   responses=error_responses(502, 404))
async def get_anime_list_entry(anilist_id: int, force_freshness: bool = False):
    return DataEnvelope(data=await UserAnimeListAPIComponent().get_anime_list_entry(anilist_id=anilist_id,
                                                                                    force_freshness=force_freshness))


@api_v1_router.put("/anime-list/{anilist_id}", response_model=DataEnvelope[UserAnimeUpdateResponse],
                   responses=error_responses(422, 502, 404))
async def update_anime_list_entry(anilist_id: int, body: UserAnimeUpdateRequest):
    return DataEnvelope(data=await UserAnimeListAPIComponent().update_anime_list_entry(anilist_id=anilist_id,
                                                                                       body=body))


@api_v1_router.delete("/anime-list/{anilist_id}", status_code=204,
                      responses=error_responses(422, 502, 404))
async def delete_anime_list_entry(anilist_id: int):
    await UserAnimeListAPIComponent().delete_anime_list_item(anilist_id=anilist_id)
