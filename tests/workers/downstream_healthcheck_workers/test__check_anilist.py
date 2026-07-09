from dataclasses import dataclass

import pytest

from common.exceptions import ExternalServiceException
from constants import ExternalServiceErrorLevel as Level, ExternalServiceCode
from workers.downstream_healthcheck_workers import ServiceStatus


@dataclass
class Case:
    id: str
    user_token: str | None = "anilist-token"
    healthcheck_exception: Exception | None = None
    pre_unhealthy: bool = False
    expected_status: ServiceStatus = None
    expected_with_auth: bool | None = None


CASES = [
    Case(id="success with token resets status",
         pre_unhealthy=True,
         expected_status=ServiceStatus("Anilist", ExternalServiceCode.ANILIST, checked=True),
         expected_with_auth=True),
    # the unauthenticated healthcheck succeeds, but with no token the status is left NOT_CONFIGURED
    Case(id="no token stays not configured even when healthcheck succeeds",
         user_token=None,
         expected_status=ServiceStatus("Anilist", ExternalServiceCode.ANILIST, healthy=False,
                                       error_level=Level.NOT_CONFIGURED,
                                       error_details="No user token set for Anilist client.",
                                       error_code=401, checked=True),
         expected_with_auth=False),
    # the failing unauthenticated healthcheck overrides the initial NOT_CONFIGURED status
    Case(id="no token with failing healthcheck reports the failure",
         user_token=None,
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=500),
         expected_status=ServiceStatus("Anilist", ExternalServiceCode.ANILIST, healthy=False,
                                       error_level=Level.DOWN, error_details="boom",
                                       error_code=500, checked=True)),
    Case(id="401-auth",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=401),
         expected_status=ServiceStatus("Anilist", ExternalServiceCode.ANILIST, healthy=False,
                                       error_level=Level.AUTH_ISSUE, error_details="boom",
                                       error_code=401, checked=True)),
    Case(id="403-auth",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=403),
         expected_status=ServiceStatus("Anilist", ExternalServiceCode.ANILIST, healthy=False,
                                       error_level=Level.AUTH_ISSUE, error_details="boom",
                                       error_code=403, checked=True)),
    Case(id="400-internal",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=400),
         expected_status=ServiceStatus("Anilist", ExternalServiceCode.ANILIST, healthy=False,
                                       error_level=Level.INTERNAL_ERROR, error_details="boom",
                                       error_code=400, checked=True)),
    Case(id="500-down",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=500),
         expected_status=ServiceStatus("Anilist", ExternalServiceCode.ANILIST, healthy=False,
                                       error_level=Level.DOWN, error_details="boom",
                                       error_code=500, checked=True)),
    Case(id="unknown-down",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=None),
         expected_status=ServiceStatus("Anilist", ExternalServiceCode.ANILIST, healthy=False,
                                       error_level=Level.DOWN, error_details="boom",
                                       error_code=None, checked=True)),
    Case(id="unexpected exception is internal error",
         healthcheck_exception=ValueError("kaboom"),
         expected_status=ServiceStatus("Anilist", ExternalServiceCode.ANILIST, healthy=False,
                                       error_level=Level.INTERNAL_ERROR,
                                       error_details="Unexpected error during healthcheck: kaboom",
                                       error_code=0, checked=True)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_check_anilist(case: Case, make_worker):
    w = make_worker()
    w._anilist_service.user_token = case.user_token
    if case.pre_unhealthy:
        w._anilist_status.healthy = False
        w._anilist_status.error_level = Level.DOWN
    if case.healthcheck_exception is not None:
        w._anilist_service.healthcheck.side_effect = case.healthcheck_exception

    await w._check_anilist()

    assert w._anilist_status == case.expected_status
    if case.expected_with_auth is not None:
        w._anilist_service.healthcheck.assert_awaited_once_with(with_auth=case.expected_with_auth)
