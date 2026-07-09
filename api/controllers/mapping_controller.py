from api.routes import api_v1_router
from api.schemas import DataEnvelope, error_responses
from api.schemas.mapping_schemas import MappingOverrideListResponse, MappingOverrideItem, MappingOverrideRequest, \
    MappingStatsResponse
from components.api_components.mapping_api_component import MappingAPIComponent


@api_v1_router.get("/mapping-overrides",
                   response_model=DataEnvelope[MappingOverrideListResponse])
async def get_mapping_overrides():
    return DataEnvelope(data=await MappingAPIComponent().get_mapping_overrides())


@api_v1_router.post("/mapping-overrides",
                    response_model=DataEnvelope[MappingOverrideItem],
                    responses=error_responses(422))
async def create_mapping_overrides(body: MappingOverrideRequest):
    return DataEnvelope(data=await MappingAPIComponent().create_mapping_override(body=body))


@api_v1_router.put("/mapping-overrides/{mapping_override_id}",
                   response_model=DataEnvelope[MappingOverrideItem],
                   responses=error_responses(404, 422))
async def update_mapping_override(mapping_override_id: int, body: MappingOverrideRequest):
    return DataEnvelope(data=await MappingAPIComponent().update_mapping_override(
        mapping_override_id=mapping_override_id, body=body
    ))


@api_v1_router.delete("/mapping-overrides/{mapping_override_id}",
                      status_code=204,
                      responses=error_responses(404))
async def delete_mapping_override(mapping_override_id: int):
    await MappingAPIComponent().delete_mapping_override(mapping_override_id=mapping_override_id)


@api_v1_router.get("/mapping-stats",
                   response_model=DataEnvelope[MappingStatsResponse])
async def get_mapping_stats():
    return DataEnvelope(data=await MappingAPIComponent().get_mapping_stats())


@api_v1_router.post("/mappings/refresh",
                    status_code=204)
async def refresh_mappings():
    return DataEnvelope(data=await MappingAPIComponent().refresh_mappings())
