from dataclasses import dataclass

import pytest

from utils.helpers.type_helpers import require_digit_str


@dataclass
class Case:
    id: str
    value: object
    nullable: bool = False
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="accepts '0'", value="0"),
    Case(id="accepts '123'", value="123"),
    Case(id="accepts '007'", value="007"),
    Case(id="accepts None when nullable", value=None, nullable=True),
    # Non-digit strings (incl. empty, signs, decimals, whitespace) and non-strings are all rejected.
    Case(id="rejects empty string", value="", expected_exception=TypeError),
    Case(id="rejects '12a'", value="12a", expected_exception=TypeError),
    Case(id="rejects '-1'", value="-1", expected_exception=TypeError),
    Case(id="rejects '1.5'", value="1.5", expected_exception=TypeError),
    Case(id="rejects ' 1'", value=" 1", expected_exception=TypeError),
    Case(id="rejects int", value=123, expected_exception=TypeError),
    Case(id="rejects bool", value=True, expected_exception=TypeError),
    Case(id="rejects None when not nullable", value=None, expected_exception=TypeError),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_require_digit_str(case: Case):
    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            require_digit_str(case.value, nullable=case.nullable)
        return
    assert require_digit_str(case.value, nullable=case.nullable) is None
