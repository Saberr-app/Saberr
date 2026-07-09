from dataclasses import dataclass

import pytest

from utils.helpers.fuzzy_matcher import fuzzy_match_language_code


@dataclass
class Case:
    id: str
    text: str
    expected_result: str


CASES = [
    Case(id="en", text="en", expected_result="EN"),
    Case(id="eng", text="eng", expected_result="EN"),
    Case(id="english", text="english", expected_result="EN"),
    Case(id="EN uppercase", text="EN", expected_result="EN"),
    Case(id="ja -> jp", text="ja", expected_result="JP"),
    Case(id="jpn -> jp", text="jpn", expected_result="JP"),
    Case(id="japanese -> jp", text="japanese", expected_result="JP"),
    Case(id="es", text="es", expected_result="ES"),
    Case(id="fr", text="fr", expected_result="FR"),
    Case(id="de", text="de", expected_result="DE"),
    Case(id="it", text="it", expected_result="IT"),
    Case(id="pt", text="pt", expected_result="PT"),
    Case(id="ru", text="ru", expected_result="RU"),
    Case(id="cn", text="cn", expected_result="CN"),
    Case(id="chinese -> cn", text="chinese", expected_result="CN"),
    Case(id="ca -> cn", text="ca", expected_result="CN"),
    # empty returned as-is
    Case(id="empty as-is", text="", expected_result=""),
    # unknown returned lowercased
    Case(id="unknown lowercased", text="xx", expected_result="xx"),
    Case(id="KLINGON lowercased", text="KLINGON", expected_result="klingon"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_fuzzy_match_language_code(case: Case):
    assert fuzzy_match_language_code(case.text) == case.expected_result
