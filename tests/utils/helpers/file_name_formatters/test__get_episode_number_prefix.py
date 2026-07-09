from dataclasses import dataclass

import pytest

from constants import EpisodeFormattingToken
from utils.helpers.file_name_formatters import _get_episode_number_prefix

_EN = EpisodeFormattingToken.EPISODE_NUMBER.value
_AB = EpisodeFormattingToken.ABSOLUTE_EPISODE_NUMBER.value


@dataclass
class Case:
    id: str
    format_: str
    token: str
    expected_result: str


CASES = [
    Case(id="single E prefix", format_="E{" + _EN + "}", token=_EN, expected_result="E"),
    Case(id="Ep prefix", format_="Ep{" + _EN + "}", token=_EN, expected_result="Ep"),
    Case(id="no prefix", format_="{" + _EN + "}", token=_EN, expected_result=""),
    Case(id="absolute token prefix", format_="E{" + _AB + "}", token=_AB, expected_result="E"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__get_episode_number_prefix(case: Case):
    assert _get_episode_number_prefix(case.format_, token=case.token) == case.expected_result
