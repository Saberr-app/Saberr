from dataclasses import dataclass

import pytest

from utils.helpers.text_helpers import clean_path_name


@dataclass
class Case:
    id: str
    raw: str
    expected_result: str


CASES = [
    Case(id="colon -> modifier letter", raw="a:b", expected_result="a꞉b"),
    Case(id="forward slash -> division slash", raw="a/b", expected_result="a∕b"),
    Case(id="backslash substituted", raw="a\\b", expected_result="a⑊b"),
    Case(id="question mark substituted", raw="a?b", expected_result="a︖b"),
    Case(id="asterisk substituted", raw="a*b", expected_result="a⁎b"),
    Case(id="pipe substituted", raw="a|b", expected_result="a⏐b"),
    Case(id="angle brackets substituted", raw="a<b>c", expected_result="a‹b›c"),
    Case(id="double quotes alternate open and close",
         raw='say "hi" and "bye"', expected_result="say “hi” and “bye”"),
    Case(id="double spaces collapsed and trimmed", raw="  a  b  c  ", expected_result="a b c"),
    Case(id="trailing dot stripped", raw="Show.", expected_result="Show"),
    Case(id="multiple trailing dots stripped", raw="Show...", expected_result="Show"),
    Case(id="trailing dots and spaces stripped", raw="Show. . ", expected_result="Show"),
    Case(id="whitespace control chars become a single space", raw="a\tb\nc", expected_result="a b c"),
    Case(id="non-whitespace control chars removed", raw="a\x00b", expected_result="ab"),
    Case(id="clean string is unchanged",
         raw="Sousou no Frieren", expected_result="Sousou no Frieren"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_clean_path_name(case: Case):
    assert clean_path_name(case.raw) == case.expected_result
