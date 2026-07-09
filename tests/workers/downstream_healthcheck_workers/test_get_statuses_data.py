from dataclasses import dataclass, field

import pytest

from constants import ExternalServiceErrorLevel


@dataclass
class Case:
    id: str
    mutate_attr: str | None = None  # worker status attribute to mark unhealthy before serializing
    error_level: ExternalServiceErrorLevel | None = None
    error_details: str | None = None
    error_code: int | None = None
    expected_keys: set | None = None
    expected_service: str = "qbit"
    expected_data: dict = field(default_factory=dict)


CASES = [
    Case(id="returns dict for every service",
         expected_keys={"qbit", "anilist", "tvdb", "rss", "notifications_discord_webhook"},
         expected_service="qbit",
         expected_data={"name": "qBittorrent", "healthy": True, "error_level": None,
                        "error_details": None, "error_code": None}),
    Case(id="serializes an unhealthy status",
         mutate_attr="_qbit_status", error_level=ExternalServiceErrorLevel.AUTH_ISSUE,
         error_details="bad creds", error_code=401,
         expected_service="qbit",
         expected_data={"name": "qBittorrent", "healthy": False,
                        "error_level": "Auth Issue",  # the enum value, not the member
                        "error_details": "bad creds", "error_code": 401}),
    Case(id="serializes a healthy status",
         expected_service="rss",
         expected_data={"name": "RSS", "healthy": True, "error_level": None,
                        "error_details": None, "error_code": None}),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_get_statuses_data(case: Case, make_worker):
    w = make_worker()
    if case.mutate_attr is not None:
        status = getattr(w, case.mutate_attr)
        status.healthy = False
        status.error_level = case.error_level
        status.error_details = case.error_details
        status.error_code = case.error_code

    data = w.get_statuses_data()

    if case.expected_keys is not None:
        assert set(data) == case.expected_keys
    assert data[case.expected_service] == case.expected_data
