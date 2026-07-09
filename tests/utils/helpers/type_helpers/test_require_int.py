from dataclasses import dataclass

import pytest

from utils.helpers.type_helpers import require_int


@dataclass
class Case:
    id: str
    value: object
    nullable: bool = False
    minimum_value: int | None = None
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="accepts 0", value=0),
    Case(id="accepts 1", value=1),
    Case(id="accepts -5", value=-5),
    Case(id="accepts 1000", value=1000),
    Case(id="accepts None when nullable", value=None, nullable=True),
    # bool is a subclass of int but must be rejected; floats/strings are not ints either.
    Case(id="rejects True", value=True, expected_exception=TypeError),
    Case(id="rejects False", value=False, expected_exception=TypeError),
    Case(id="rejects float", value=1.5, expected_exception=TypeError),
    Case(id="rejects string", value="1", expected_exception=TypeError),
    Case(id="rejects list", value=[1], expected_exception=TypeError),
    Case(id="rejects None when not nullable", value=None, expected_exception=TypeError),
    Case(id="at minimum is allowed", value=5, minimum_value=5),
    Case(id="below minimum raises", value=4, minimum_value=5, expected_exception=ValueError),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_require_int(case: Case):
    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            require_int(case.value, nullable=case.nullable, minimum_value=case.minimum_value)
        return
    assert require_int(case.value, nullable=case.nullable, minimum_value=case.minimum_value) is None
