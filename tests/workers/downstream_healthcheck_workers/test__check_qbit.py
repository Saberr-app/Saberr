from dataclasses import dataclass

import pytest

from common.exceptions import ExternalServiceException
from config import config
from constants import ExternalServiceErrorLevel as Level, ExternalServiceCode
from workers.downstream_healthcheck_workers import ServiceStatus


@pytest.fixture(autouse=True)
def _configured_qbit(monkeypatch):
    # qBit is only healthchecked when a base url is configured; the tests below exercise that branch.
    monkeypatch.setattr(config.user_settings, "qbit_base_url", "http://qbit.test")


@dataclass
class Case:
    id: str
    qbit_base_url: str | None = "http://qbit.test"
    healthcheck_exception: Exception | None = None
    pre_unhealthy: bool = False
    expected_status: ServiceStatus = None
    expected_healthcheck_awaited: bool = True


CASES = [
    Case(id="no base url is not configured",
         qbit_base_url=None,
         expected_status=ServiceStatus("qBittorrent", ExternalServiceCode.QBIT, healthy=False,
                                       error_level=Level.NOT_CONFIGURED,
                                       error_details="No host set for qBittorrent client.",
                                       error_code=401, checked=True),
         expected_healthcheck_awaited=False),
    Case(id="success resets status",
         pre_unhealthy=True,
         expected_status=ServiceStatus("qBittorrent", ExternalServiceCode.QBIT, checked=True)),
    Case(id="401-auth",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=401),
         expected_status=ServiceStatus("qBittorrent", ExternalServiceCode.QBIT, healthy=False,
                                       error_level=Level.AUTH_ISSUE, error_details="boom",
                                       error_code=401, checked=True)),
    Case(id="403-auth",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=403),
         expected_status=ServiceStatus("qBittorrent", ExternalServiceCode.QBIT, healthy=False,
                                       error_level=Level.AUTH_ISSUE, error_details="boom",
                                       error_code=403, checked=True)),
    Case(id="400-internal",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=400),
         expected_status=ServiceStatus("qBittorrent", ExternalServiceCode.QBIT, healthy=False,
                                       error_level=Level.INTERNAL_ERROR, error_details="boom",
                                       error_code=400, checked=True)),
    Case(id="500-down",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=500),
         expected_status=ServiceStatus("qBittorrent", ExternalServiceCode.QBIT, healthy=False,
                                       error_level=Level.DOWN, error_details="boom",
                                       error_code=500, checked=True)),
    Case(id="unknown-down",
         healthcheck_exception=ExternalServiceException(detail="boom", status_code=None),
         expected_status=ServiceStatus("qBittorrent", ExternalServiceCode.QBIT, healthy=False,
                                       error_level=Level.DOWN, error_details="boom",
                                       error_code=None, checked=True)),
    Case(id="unexpected exception is internal error",
         healthcheck_exception=ValueError("kaboom"),
         expected_status=ServiceStatus("qBittorrent", ExternalServiceCode.QBIT, healthy=False,
                                       error_level=Level.INTERNAL_ERROR,
                                       error_details="Unexpected error during healthcheck: kaboom",
                                       error_code=0, checked=True)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_check_qbit(case: Case, make_worker, monkeypatch):
    monkeypatch.setattr(config.user_settings, "qbit_base_url", case.qbit_base_url)
    w = make_worker()
    if case.pre_unhealthy:
        w._qbit_status.healthy = False  # pretend a previous run had failed
        w._qbit_status.error_level = Level.DOWN
    if case.healthcheck_exception is not None:
        w._qbit_service.healthcheck.side_effect = case.healthcheck_exception

    await w._check_qbit()

    assert w._qbit_status == case.expected_status
    if case.expected_healthcheck_awaited:
        w._qbit_service.healthcheck.assert_awaited()
    else:
        w._qbit_service.healthcheck.assert_not_awaited()
