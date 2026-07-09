from datetime import datetime

from sqlalchemy import select, cast, String

from dto.orm_models import AuditLog
from constants import AuditLogCategory, AuditLogCode, SortDirection
from repositories import BaseRepo


class AuditLogRepo(BaseRepo):

    # noinspection PyTypeChecker
    async def create_audit_log(self,
                               code: AuditLogCode,
                               category: AuditLogCategory,
                               text: str,
                               data: dict,
                               context_id: str) -> AuditLog:
        audit_log = AuditLog(
            code=code,
            category=category,
            text=text,
            data=data,
            context_id=context_id
        )
        self._session.add(audit_log)
        await self._session.flush()
        return audit_log

    async def get_audit_logs(self,
                             categories: list[AuditLogCategory] | None = None,
                             codes: list[AuditLogCode] | None = None,
                             text_query: str | None = None,
                             data_query: str | None = None,
                             context_id: str | None = None,
                             created_after: datetime | None = None,
                             created_before: datetime | None = None,
                             sort_direction: SortDirection = SortDirection.DESC,
                             limit: int | None = None,
                             offset: int | None = None) -> list[AuditLog]:
        query = select(AuditLog)
        if categories:
            query = query.where(AuditLog.category.in_(categories))
        if codes:
            query = query.where(AuditLog.code.in_(codes))
        if text_query:
            query = query.where(AuditLog.text.ilike(f"%{text_query}%"))
        if data_query:
            # data is a Json-decorated column; cast to text so the LIKE pattern isn't JSON-encoded.
            query = query.where(cast(AuditLog.data, String).ilike(f"%{data_query}%"))
        if context_id:
            query = query.where(AuditLog.context_id == context_id)
        if created_after:
            query = query.where(AuditLog.created_at > created_after)
        if created_before:
            query = query.where(AuditLog.created_at < created_before)
        if sort_direction == SortDirection.ASC:
            query = query.order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
        else:
            query = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        result = await self._session.execute(query)
        return result.scalars().all()
