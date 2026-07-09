from dataclasses import dataclass

import pytest

from components.audit_log_component import _create_audit_log
from constants import AuditLogCode, AUDIT_LOG_CODE_TO_CATEGORY_MAP

_REPO = "repositories.audit_log_repo.AuditLogRepo"


@dataclass
class Case:
    id: str
    yielded: list
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="persists the three yielded items",
         yielded=[AuditLogCode.APP_STARTED, "Saberr is starting", {"app_version": "1.0"}]),
    Case(id="rejects generators that do not yield exactly three",
         yielded=[AuditLogCode.APP_STARTED, "only two"], expected_exception=ValueError),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test__create_audit_log(case: Case, mocker):
    create = mocker.patch(f"{_REPO}.create_audit_log")

    async def generator():
        for item in case.yielded:
            yield item

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await _create_audit_log(generator)()
        return

    await _create_audit_log(generator)()

    create.assert_awaited_once()
    kwargs = create.await_args.kwargs
    assert kwargs["code"] == case.yielded[0]
    assert kwargs["category"] == AUDIT_LOG_CODE_TO_CATEGORY_MAP[case.yielded[0]]
    assert kwargs["text"] == case.yielded[1]
    assert kwargs["data"] == case.yielded[2]
