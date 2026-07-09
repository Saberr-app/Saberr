from dataclasses import dataclass

import pytest

from constants import VideoSource
from utils.helpers.fuzzy_matcher import fuzzy_match_video_source


@dataclass
class Case:
    id: str
    text: str
    expected_result: VideoSource


CASES = [
    Case(id="crunchyroll name", text="Crunchyroll", expected_result=VideoSource.CRUNCHYROLL),
    Case(id="crunchyroll tag", text="[CR]", expected_result=VideoSource.CRUNCHYROLL),
    Case(id="netflix name", text="Netflix", expected_result=VideoSource.NETFLIX),
    Case(id="netflix abbrev", text="NF", expected_result=VideoSource.NETFLIX),
    Case(id="amazon prime", text="Amazon Prime", expected_result=VideoSource.AMAZON),
    Case(id="disney plus symbol", text="disney+", expected_result=VideoSource.DISNEY_PLUS),
    Case(id="disney plus words", text="Disney Plus", expected_result=VideoSource.DISNEY_PLUS),
    Case(id="adn full name", text="anime digital network", expected_result=VideoSource.ADN),
    Case(id="hidive", text="HIDIVE", expected_result=VideoSource.HIDIVE),
    Case(id="hulu", text="hulu", expected_result=VideoSource.HULU),
    Case(id="empty -> OTHER (not None)", text="", expected_result=VideoSource.OTHER),
    Case(id="unknown service -> OTHER", text="unknown service", expected_result=VideoSource.OTHER),
    # 'cr' substring must not false-match anymore
    Case(id="cr substring no false match", text="scared", expected_result=VideoSource.OTHER),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_fuzzy_match_video_source(case: Case):
    assert fuzzy_match_video_source(case.text) == case.expected_result
