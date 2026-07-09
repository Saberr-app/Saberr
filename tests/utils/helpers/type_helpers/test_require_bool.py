from dataclasses import dataclass

import pytest

from utils.helpers.type_helpers import require_bool


@dataclass
class Case:
    id: str
    value: object
    nullable: bool = False
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="accepts True", value=True),
    Case(id="accepts False", value=False),
    Case(id="accepts None when nullable", value=None, nullable=True),
    # 0 and 1 are ints, not bools, so they must be rejected
    Case(id="rejects 0", value=0, expected_exception=TypeError),
    Case(id="rejects 1", value=1, expected_exception=TypeError),
    Case(id="rejects float", value=1.0, expected_exception=TypeError),
    Case(id="rejects string", value="true", expected_exception=TypeError),
    Case(id="rejects list", value=[], expected_exception=TypeError),
    Case(id="rejects None when not nullable", value=None, expected_exception=TypeError),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_require_bool(case: Case):
    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            require_bool(case.value, nullable=case.nullable)
        return
    assert require_bool(case.value, nullable=case.nullable) is None
