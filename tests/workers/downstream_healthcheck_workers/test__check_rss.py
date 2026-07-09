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


# RSS has no auth, so only 400 is INTERNAL_ERROR; everything else (incl. 401/403) is DOWN.
CASES = [
    Case(id="success resets status",
         pre_unhealthy=True,
         expected_status=ServiceStatus("RSS", ExternalServiceCode.RSS, checked=True)),
    Case(id="400-internal",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=400),
         expected_status=ServiceStatus("RSS", ExternalServiceCode.RSS, healthy=False,
                                       error_level=Level.INTERNAL_ERROR, error_details="boom",
                                       error_code=400, checked=True)),
    Case(id="401-down",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=401),
         expected_status=ServiceStatus("RSS", ExternalServiceCode.RSS, healthy=False,
                                       error_level=Level.DOWN, error_details="boom",
                                       error_code=401, checked=True)),
    Case(id="403-down",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=403),
         expected_status=ServiceStatus("RSS", ExternalServiceCode.RSS, healthy=False,
                                       error_level=Level.DOWN, error_details="boom",
                                       error_code=403, checked=True)),
    Case(id="500-down",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=500),
         expected_status=ServiceStatus("RSS", ExternalServiceCode.RSS, healthy=False,
                                       error_level=Level.DOWN, error_details="boom",
                                       error_code=500, checked=True)),
    Case(id="unknown-down",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=None),
         expected_status=ServiceStatus("RSS", ExternalServiceCode.RSS, healthy=False,
                                       error_level=Level.DOWN, error_details="boom",
                                       error_code=None, checked=True)),
    Case(id="unexpected exception is internal error",
         healthcheck_exception=ValueError("kaboom"),
         expected_status=ServiceStatus("RSS", ExternalServiceCode.RSS, healthy=False,
                                       error_level=Level.INTERNAL_ERROR,
                                       error_details="Unexpected error during healthcheck: kaboom",
                                       error_code=0, checked=True)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_check_rss(case: Case, make_worker):
    w = make_worker()
    if case.pre_unhealthy:
        w._rss_status.healthy = False
        w._rss_status.error_level = Level.DOWN
    if case.healthcheck_exception is not None:
        w._rss_service.healthcheck.side_effect = case.healthcheck_exception

    await w._check_rss()

    assert w._rss_status == case.expected_status
