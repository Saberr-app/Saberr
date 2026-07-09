from dataclasses import dataclass

import pytest

from utils.helpers.type_helpers import require_str


@dataclass
class Case:
    id: str
    value: object
    nullable: bool = False
    max_length: int | None = None
    new_lines_allowed: bool = True
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="accepts empty string", value=""),
    Case(id="accepts 'hello'", value="hello"),
    Case(id="accepts multi-line string", value="multi\nline"),
    Case(id="accepts long string", value="x" * 1000),
    Case(id="accepts None when nullable", value=None, nullable=True),
    Case(id="rejects int", value=1, expected_exception=TypeError),
    Case(id="rejects float", value=1.5, expected_exception=TypeError),
    Case(id="rejects bool", value=True, expected_exception=TypeError),
    Case(id="rejects bytes", value=b"bytes", expected_exception=TypeError),
    Case(id="rejects list", value=["a"], expected_exception=TypeError),
    Case(id="rejects None when not nullable", value=None, expected_exception=TypeError),
    Case(id="within max_length is allowed", value="abc", max_length=3),
    Case(id="exceeding max_length raises", value="abcd", max_length=3, expected_exception=ValueError),
    Case(id="newline allowed by default", value="a\nb"),
    Case(id="newline rejected when not allowed", value="a\nb", new_lines_allowed=False,
         expected_exception=ValueError),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_require_str(case: Case):
    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            require_str(case.value, nullable=case.nullable, max_length=case.max_length,
                        new_lines_allowed=case.new_lines_allowed)
        return
    assert require_str(case.value, nullable=case.nullable, max_length=case.max_length,
                       new_lines_allowed=case.new_lines_allowed) is None
