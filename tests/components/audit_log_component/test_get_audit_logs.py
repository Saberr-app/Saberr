from dataclasses import dataclass, field

import pytest

from components.audit_log_component import AuditLogComponent
from constants import AuditLogCategory, AuditLogCode, SortDirection


@dataclass
class Case:
    id: str
    call_kwargs: dict = field(default_factory=dict)


CASES = [
    Case(id="forwards no filters by default", call_kwargs={}),
    Case(id="forwards category filter",
         call_kwargs=dict(categories=[AuditLogCategory.APP])),
    Case(id="forwards text query", call_kwargs=dict(text_query="login")),
    Case(id="forwards limit", call_kwargs=dict(limit=1)),
    Case(id="forwards sort direction",
         call_kwargs=dict(sort_direction=SortDirection.ASC, limit=None)),
]

# default values the component applies to every repo call
_DEFAULTS = dict(categories=None, codes=None, text_query=None, data_query=None, context_id=None,
                 created_after=None, created_before=None, sort_direction=SortDirection.DESC,
                 limit=None, offset=None)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_audit_logs(case: Case, mocker):
    expected = [object()]
    repo_get = mocker.patch(
        "repositories.audit_log_repo.AuditLogRepo.get_audit_logs", return_value=expected)

    result = await AuditLogComponent().get_audit_logs(**case.call_kwargs)

    assert result is expected
    repo_get.assert_awaited_once_with(**{**_DEFAULTS, **case.call_kwargs})
