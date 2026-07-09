from typing import Annotated

from fastapi import Query

from api.routes import api_v1_router
from components.api_components.audit_log_api_component import AuditLogsAPIComponent
from api.schemas import DataEnvelope
from api.schemas.audit_log_schemas import AuditLogListRequest, AuditLogListResponse


@api_v1_router.get("/audit-logs", response_model=DataEnvelope[AuditLogListResponse])
async def list_audit_logs(params: Annotated[AuditLogListRequest, Query()]):
    return DataEnvelope(data=await AuditLogsAPIComponent().get_audit_logs(params=params))
