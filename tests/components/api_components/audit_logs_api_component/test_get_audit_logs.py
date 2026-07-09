from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from typing import Callable

import pytest

from components.api_components.audit_log_api_component import AuditLogsAPIComponent
from constants import AuditLogCategory, AuditLogCode, SortDirection
from api.schemas.audit_log_schemas import AuditLogListRequest


@dataclass
class Case:
    id: str
    request_factory: Callable[[], AuditLogListRequest] = field(default_factory=lambda: AuditLogListRequest)
    # subset of kwargs expected to be forwarded to the underlying component
    expected_forwarded: dict = field(default_factory=dict)
    assert_mapped_item: bool = False


CASES = [
    Case(id="forwards defaults and maps items",
         request_factory=AuditLogListRequest, assert_mapped_item=True),
    Case(id="forwards category filter",
         request_factory=lambda: AuditLogListRequest(categories=[AuditLogCategory.APP]),
         expected_forwarded={"categories": [AuditLogCategory.APP]}),
    Case(id="forwards code filter",
         request_factory=lambda: AuditLogListRequest(codes=[AuditLogCode.TORRENT_SELECTED]),
         expected_forwarded={"codes": [AuditLogCode.TORRENT_SELECTED]}),
    Case(id="forwards text query",
         request_factory=lambda: AuditLogListRequest(text_query="login"),
         expected_forwarded={"text_query": "login"}),
    Case(id="forwards data query",
         request_factory=lambda: AuditLogListRequest(data_query="deadbeef"),
         expected_forwarded={"data_query": "deadbeef"}),
    Case(id="forwards context_id",
         request_factory=lambda: AuditLogListRequest(context_id="ctx-1"),
         expected_forwarded={"context_id": "ctx-1"}),
    Case(id="forwards limit and offset",
         request_factory=lambda: AuditLogListRequest(limit=1, offset=1),
         expected_forwarded={"limit": 1, "offset": 1}),
    Case(id="forwards sort direction",
         request_factory=lambda: AuditLogListRequest(sort_direction=SortDirection.ASC),
         expected_forwarded={"sort_direction": SortDirection.ASC}),
    Case(id="forwards created_after",
         request_factory=lambda: AuditLogListRequest(
             created_after=datetime(2030, 1, 1, tzinfo=UTC)),
         expected_forwarded={"created_after": datetime(2030, 1, 1, tzinfo=UTC)}),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_audit_logs(case: Case, make_audit_log, mocker):
    audit_log = make_audit_log(code=AuditLogCode.LOGIN_SUCCEEDED, text="User login succeeded",
                               data={"ip_address": "1.2.3.4"}, context_id="ctx-1")
    component_get = mocker.patch(
        "components.audit_log_component.AuditLogComponent.get_audit_logs", return_value=[audit_log])

    result = await AuditLogsAPIComponent().get_audit_logs(params=case.request_factory())

    forwarded = component_get.await_args.kwargs
    for key, value in case.expected_forwarded.items():
        assert forwarded[key] == value

    if case.assert_mapped_item:
        item = result.audit_logs[0]
        assert item.id == audit_log.id
        assert item.code is AuditLogCode.LOGIN_SUCCEEDED
        assert item.category is AuditLogCategory.APP
        assert item.text == "User login succeeded"
        assert item.data == {"ip_address": "1.2.3.4"}
        assert item.context_id == "ctx-1"
