from dataclasses import dataclass

import pytest

from utils.helpers.fuzzy_matcher import _contains_token


@dataclass
class Case:
    id: str
    text: str
    keyword: str
    expected_result: bool


CASES = [
    Case(id="standalone token matches", text="cr web-dl", keyword="cr", expected_result=True),
    Case(id="token embedded in a word does not match", text="crunchyroll", keyword="cr", expected_result=False),
    Case(id="token bounded by non-alphanumerics matches", text="1080p hd", keyword="hd", expected_result=True),
    Case(id="absent token", text="1080p hevc", keyword="cr", expected_result=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__contains_token(case: Case):
    assert _contains_token(case.text, case.keyword) == case.expected_result
