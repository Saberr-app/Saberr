from dataclasses import dataclass, field

import pytest

from utils.helpers.text_helpers import validate_format_tokens


@dataclass
class Case:
    id: str
    text: str
    allowed: list[str] = field(default_factory=lambda: ["a", "b"])
    expected_exception: type[Exception] | None = None
    expected_match: str | None = None


CASES = [
    Case(id="all tokens allowed", text="{a} and {b}"),
    Case(id="repeated tokens are fine", text="{a}{a}{b}"),
    Case(id="no tokens at all", text="no tokens at all"),
    Case(id="escaped braces are literal", text="{{a}} is escaped"),
    Case(id="empty string", text=""),
    Case(id="unknown token raises with its name", text="{a} and {c}",
         expected_exception=ValueError, expected_match="Invalid format token: c"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_validate_format_tokens(case: Case):
    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception, match=case.expected_match):
            validate_format_tokens(case.text, case.allowed)
        return
    assert validate_format_tokens(case.text, case.allowed) is None
