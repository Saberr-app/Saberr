from dataclasses import dataclass
from typing import Callable

import pytest

from constants import ExternalServiceErrorLevel, ExternalServiceCode
from workers.downstream_healthcheck_workers import ServiceStatus


@dataclass
class Case:
    id: str
    make_status: Callable[[], ServiceStatus]
    # action to run on the status before asserting (e.g. reset); identity by default
    action: Callable[[ServiceStatus], None] = lambda s: None
    expected_fields: tuple | None = None  # (healthy, error_level, error_details, error_code)
    expected_to_dict: dict | None = None
    expected_to_dict_error_level_is_none: bool = False
    expected_equals: ServiceStatus | None = None


CASES = [
    Case(id="defaults are healthy",
         make_status=lambda: ServiceStatus("qBittorrent", ExternalServiceCode.QBIT),
         expected_fields=(True, None, None, None)),
    Case(id="to_dict omits code and unwraps error_level",
         make_status=lambda: ServiceStatus("qBittorrent", ExternalServiceCode.QBIT, healthy=False,
                                           error_level=ExternalServiceErrorLevel.DOWN,
                                           error_details="boom", error_code=500),
         expected_to_dict={"name": "qBittorrent", "healthy": False, "error_level": "Down",
                           "error_details": "boom", "error_code": 500}),
    Case(id="to_dict keeps error_level none when unset",
         make_status=lambda: ServiceStatus("RSS", ExternalServiceCode.RSS),
         expected_to_dict_error_level_is_none=True),
    Case(id="reset clears error fields and marks healthy",
         make_status=lambda: ServiceStatus("TVDB", ExternalServiceCode.TVDB, healthy=False,
                                           error_level=ExternalServiceErrorLevel.AUTH_ISSUE,
                                           error_details="nope", error_code=401),
         action=lambda s: s.reset(),
         expected_equals=ServiceStatus("TVDB", ExternalServiceCode.TVDB)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_service_status(case: Case):
    status = case.make_status()
    case.action(status)

    if case.expected_fields is not None:
        assert (status.healthy, status.error_level, status.error_details, status.error_code) == case.expected_fields
    if case.expected_to_dict is not None:
        assert status.to_dict() == case.expected_to_dict
    if case.expected_to_dict_error_level_is_none:
        assert status.to_dict()["error_level"] is None
    if case.expected_equals is not None:
        assert status == case.expected_equals
