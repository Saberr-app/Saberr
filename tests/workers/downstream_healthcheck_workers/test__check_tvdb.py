from dataclasses import dataclass

import pytest

from common.exceptions import ExternalServiceException
from constants import ExternalServiceErrorLevel as Level, ExternalServiceCode
from workers.downstream_healthcheck_workers import ServiceStatus


@dataclass
class Case:
    id: str
    healthcheck_exception: Exception | None = None
    pre_unhealthy: bool = False
    expected_status: ServiceStatus = None


CASES = [
    Case(id="success resets status",
         pre_unhealthy=True,
         expected_status=ServiceStatus("TVDB", ExternalServiceCode.TVDB, checked=True)),
    Case(id="401-auth",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=401),
         expected_status=ServiceStatus("TVDB", ExternalServiceCode.TVDB, healthy=False,
                                       error_level=Level.AUTH_ISSUE, error_details="boom",
                                       error_code=401, checked=True)),
    Case(id="403-auth",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=403),
         expected_status=ServiceStatus("TVDB", ExternalServiceCode.TVDB, healthy=False,
                                       error_level=Level.AUTH_ISSUE, error_details="boom",
                                       error_code=403, checked=True)),
    Case(id="400-internal",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=400),
         expected_status=ServiceStatus("TVDB", ExternalServiceCode.TVDB, healthy=False,
                                       error_level=Level.INTERNAL_ERROR, error_details="boom",
                                       error_code=400, checked=True)),
    Case(id="500-down",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=500),
         expected_status=ServiceStatus("TVDB", ExternalServiceCode.TVDB, healthy=False,
                                       error_level=Level.DOWN, error_details="boom",
                                       error_code=500, checked=True)),
    Case(id="unknown-down",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=None),
         expected_status=ServiceStatus("TVDB", ExternalServiceCode.TVDB, healthy=False,
                                       error_level=Level.DOWN, error_details="boom",
                                       error_code=None, checked=True)),
    Case(id="unexpected exception is internal error",
         healthcheck_exception=ValueError("kaboom"),
         expected_status=ServiceStatus("TVDB", ExternalServiceCode.TVDB, healthy=False,
                                       error_level=Level.INTERNAL_ERROR,
                                       error_details="Unexpected error during healthcheck: kaboom",
                                       error_code=0, checked=True)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_check_tvdb(case: Case, make_worker):
    w = make_worker()
    if case.pre_unhealthy:
        w._tvdb_status.healthy = False
        w._tvdb_status.error_level = Level.DOWN
    if case.healthcheck_exception is not None:
        w._tvdb_service.healthcheck.side_effect = case.healthcheck_exception

    await w._check_tvdb()

    assert w._tvdb_status == case.expected_status
