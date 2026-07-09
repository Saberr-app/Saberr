from dataclasses import dataclass

import pytest

from utils.helpers.fuzzy_matcher import _audio_languages


@dataclass
class Case:
    id: str
    text: str
    expected_result: set[str]


CASES = [
    Case(id="two recognized audio languages", text="English Japanese", expected_result={"EN", "JP"}),
    Case(id="single recognized language", text="English", expected_result={"EN"}),
    # a language immediately followed by "sub" denotes subtitles, not an audio track
    Case(id="subtitle language is excluded", text="English Sub", expected_result=set()),
    Case(id="no recognizable language", text="Opus AAC", expected_result=set()),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__audio_languages(case: Case):
    assert _audio_languages(case.text) == case.expected_result
