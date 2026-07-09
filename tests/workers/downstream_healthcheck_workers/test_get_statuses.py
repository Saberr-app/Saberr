from dataclasses import dataclass, field

import pytest

from constants import ExternalServiceCode


@dataclass
class Case:
    id: str
    expected_keys: set = field(default_factory=set)
    # (dict key, worker attribute) the returned value must be identical to
    expected_identity: tuple[ExternalServiceCode, str] | None = None


CASES = [
    Case(id="returns all six services keyed by code",
         expected_keys={ExternalServiceCode.QBIT, ExternalServiceCode.ANILIST, ExternalServiceCode.TVDB,
                        ExternalServiceCode.RSS, ExternalServiceCode.NOTIFICATIONS_DISCORD_WEBHOOK}),
    # not copies: mutating the returned object mutates the worker's state
    Case(id="returns the live status objects",
         expected_identity=(ExternalServiceCode.QBIT, "_qbit_status")),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_get_statuses(case: Case, make_worker):
    w = make_worker()
    statuses = w.get_statuses()

    if case.expected_keys:
        assert set(statuses) == case.expected_keys
    if case.expected_identity is not None:
        key, attr = case.expected_identity
        assert statuses[key] is getattr(w, attr)
