from typing import Annotated

from fastapi import Query

from api.routes import api_v1_router
from components.api_components.schedule_api_component import ScheduleAPIComponent
from api.schemas import DataEnvelope, error_responses
from api.schemas.schedule_schemas import AiringScheduleListRequest, AiringScheduleListResponse


@api_v1_router.get("/schedule", response_model=DataEnvelope[AiringScheduleListResponse],
                   responses=error_responses(502, 422))
async def get_airing_schedule(params: Annotated[AiringScheduleListRequest, Query()]):
    return DataEnvelope(data=await ScheduleAPIComponent().get_airing_schedule(params=params))
