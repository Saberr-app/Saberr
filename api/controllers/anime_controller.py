from typing import Annotated

from fastapi import Query

from api.routes import api_v1_router
from components.api_components.anime_api_component import AnimeAPIComponent
from api.schemas import DataEnvelope, error_responses
from api.schemas.anime_schemas import (AnimeListRequest, AnimeListResponse, AnilistMetadataResponse,
                                       AnimeItemWithUserEntry, AnimeExtras, AnimeTitlesResponse)


@api_v1_router.get("/anime", response_model=DataEnvelope[AnimeListResponse],
                   responses=error_responses(502, 422))
async def get_list_of_anime(params: Annotated[AnimeListRequest, Query()]):
    return DataEnvelope(data=await AnimeAPIComponent().get_list_of_anime(params=params))


@api_v1_router.get("/anime/anilist-metadata", response_model=DataEnvelope[AnilistMetadataResponse],
                   responses=error_responses(502))
async def get_anilist_metadata():
    return DataEnvelope(data=await AnimeAPIComponent().get_anilist_metadata())


@api_v1_router.get("/anime/{anilist_id}", response_model=DataEnvelope[AnimeItemWithUserEntry],
                   responses=error_responses(502, 422, 404))
async def get_anime(anilist_id: int, force_freshness: bool = False):
    return DataEnvelope(data=await AnimeAPIComponent().get_anime(anilist_id=anilist_id,
                                                                 force_freshness=force_freshness))


@api_v1_router.get("/anime/{anilist_id}/extras", response_model=DataEnvelope[AnimeExtras],
                   responses=error_responses(502, 404))
async def get_anime_extras(anilist_id: int, force_freshness: bool = False):
    return DataEnvelope(data=await AnimeAPIComponent().get_anime_extras(anilist_id=anilist_id,
                                                                        force_freshness=force_freshness))


@api_v1_router.get("/anime/{anilist_id}/titles", response_model=DataEnvelope[AnimeTitlesResponse],
                   responses=error_responses(502, 404))
async def get_anime_titles(anilist_id: int, force_freshness: bool = False):
    return DataEnvelope(data=await AnimeAPIComponent().get_anime_titles(anilist_id=anilist_id,
                                                                        force_freshness=force_freshness))
