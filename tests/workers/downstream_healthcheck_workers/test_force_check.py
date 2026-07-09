from dataclasses import dataclass, field

import pytest


@dataclass
class Case:
    id: str
    expected_calls: list = field(default_factory=list)


CASES = [
    Case(id="force_check delegates to check with notifications disabled",
         expected_calls=[{"service_code": None, "send_notification_on_change": False}]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_force_check(case: Case, make_worker, monkeypatch):
    w = make_worker()
    calls = []

    async def fake_check(service_code=None, send_notification_on_change=True):
        calls.append({"service_code": service_code, "send_notification_on_change": send_notification_on_change})

    monkeypatch.setattr(w, "poll_downstream_status", fake_check)
    await w.force_check()
    assert calls == case.expected_calls
