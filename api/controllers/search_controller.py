from api.routes import api_v1_router
from api.schemas import DataEnvelope
from api.schemas.search_schema import SearchRequest, SearchResponse, SearchTVDBResponse
from components.api_components.search_api_component import SearchAPIComponent


@api_v1_router.post("/search", response_model=DataEnvelope[SearchResponse])
async def search(body: SearchRequest):
    return DataEnvelope(data=await SearchAPIComponent().search(body=body))


@api_v1_router.post("/search/tvdb", response_model=DataEnvelope[SearchTVDBResponse])
async def search_tvdb(body: SearchRequest):
    return DataEnvelope(data=await SearchAPIComponent().search_tvdb(body=body))
