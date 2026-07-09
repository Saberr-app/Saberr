from dataclasses import dataclass

import pytest

from utils.helpers.text_helpers import clean_text_with_html_tags


@dataclass
class Case:
    id: str
    html: str
    expected_result: str
    extra_patterns: str | None = None


CASES = [
    Case(id="strips a paragraph tag", html="<p>Hello</p>", expected_result="Hello"),
    Case(id="strips multiple inline tags", html="<b>Hi</b> <i>there</i>", expected_result="Hi there"),
    Case(id="leaves untagged text", html="no tags", expected_result="no tags"),
    Case(id="trims surrounding whitespace", html="  <p>trim me</p>  ", expected_result="trim me"),
    Case(id="self-closing tag becomes empty", html="<br/>", expected_result=""),
    Case(id="extra patterns removed before tags",
         html="<p>Hello (Source: ANN)</p>", extra_patterns=r"\(Source.*?\)", expected_result="Hello"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_clean_text_with_html_tags(case: Case):
    assert clean_text_with_html_tags(case.html, extra_patterns=case.extra_patterns) == case.expected_result
