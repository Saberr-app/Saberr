from datetime import datetime

from pydantic import BaseModel

from constants import AuditLogCategory, AuditLogCode, SortDirection


class AuditLogListRequest(BaseModel):
    categories: list[AuditLogCategory] = []
    codes: list[AuditLogCode] = []
    context_id: str | None = None
    text_query: str | None = None
    data_query: str | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    sort_direction: SortDirection = SortDirection.DESC
    offset: int = 0
    limit: int = 20


class AuditLogItem(BaseModel):
    id: int
    code: AuditLogCode
    category: AuditLogCategory
    text: str
    data: dict
    context_id: str
    created_at: datetime


class AuditLogListResponse(BaseModel):
    audit_logs: list[AuditLogItem]
