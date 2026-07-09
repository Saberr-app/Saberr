from dataclasses import dataclass

import pytest

from constants import Encoding
from utils.helpers.fuzzy_matcher import fuzzy_match_encoding


@dataclass
class Case:
    id: str
    text: str
    expected_result: Encoding | None


CASES = [
    Case(id="x265", text="x265", expected_result=Encoding.HEVC),
    Case(id="h265", text="h265", expected_result=Encoding.HEVC),
    Case(id="h.265", text="h.265", expected_result=Encoding.HEVC),
    Case(id="HEVC", text="HEVC", expected_result=Encoding.HEVC),
    # matches as a standalone token
    Case(id="10bit x265 token", text="10bit x265", expected_result=Encoding.HEVC),
    Case(id="x264", text="x264", expected_result=Encoding.AVC),
    Case(id="h.264", text="h.264", expected_result=Encoding.AVC),
    Case(id="avc lowercase", text="avc", expected_result=Encoding.AVC),
    Case(id="AVC uppercase", text="AVC", expected_result=Encoding.AVC),
    Case(id="AV1", text="AV1", expected_result=Encoding.AV1),
    Case(id="empty -> None", text="", expected_result=None),
    Case(id="vp9 -> None", text="vp9", expected_result=None),
    Case(id="xvid -> None", text="xvid", expected_result=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_fuzzy_match_encoding(case: Case):
    assert fuzzy_match_encoding(case.text) == case.expected_result
