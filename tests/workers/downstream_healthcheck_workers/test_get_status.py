from dataclasses import dataclass

import pytest


@dataclass
class Case:
    id: str
    service_code: str
    expected_attr: str | None = None  # worker attribute the result should be identical to
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="returns the requested status object",
         service_code="tvdb", expected_attr="_tvdb_status"),
    Case(id="unknown service code raises value error",
         service_code="does_not_exist", expected_exception=ValueError),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_get_status(case: Case, make_worker):
    w = make_worker()
    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            w.get_status(case.service_code)
    else:
        assert w.get_status(case.service_code) is getattr(w, case.expected_attr)
