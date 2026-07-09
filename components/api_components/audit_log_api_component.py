from common.decorators import api_component
from components import BaseComponent
from api.schemas.audit_log_schemas import AuditLogListRequest, AuditLogListResponse, AuditLogItem
from components.audit_log_component import AuditLogComponent


class AuditLogsAPIComponent(BaseComponent):

    @api_component
    async def get_audit_logs(self, params: AuditLogListRequest) -> AuditLogListResponse:
        audit_logs = await AuditLogComponent().get_audit_logs(
            categories=params.categories,
            codes=params.codes,
            text_query=params.text_query,
            data_query=params.data_query,
            context_id=params.context_id,
            created_after=params.created_after,
            created_before=params.created_before,
            sort_direction=params.sort_direction,
            limit=params.limit,
            offset=params.offset,
        )
        return AuditLogListResponse(audit_logs=[
            AuditLogItem(
                id=audit_log.id,
                code=audit_log.code,
                category=audit_log.category,
                text=audit_log.text,
                data=audit_log.data,
                context_id=audit_log.context_id,
                created_at=audit_log.created_at,
            ) for audit_log in audit_logs
        ])
