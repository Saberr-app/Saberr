from dataclasses import dataclass

import pytest

from constants import EpisodeFormattingToken
from utils.helpers.file_name_formatters import _get_episode_number_string

_EN = EpisodeFormattingToken.EPISODE_NUMBER.value
_PREFIXED = "E{" + _EN + "}"
_PLAIN = "{" + _EN + "}"


@dataclass
class Case:
    id: str
    format_: str
    episode_numbers: list[int]
    padding: int
    are_continuous: bool
    expected_result: str


CASES = [
    Case(id="continuous range repeats the prefix on the upper bound",
         format_=_PREFIXED, episode_numbers=[1, 2, 3], padding=2, are_continuous=True,
         expected_result="01-E03"),
    Case(id="single number is just padded", format_=_PREFIXED, episode_numbers=[5], padding=2,
         are_continuous=True, expected_result="05"),
    Case(id="non-continuous with prefix joins on the prefix", format_=_PREFIXED,
         episode_numbers=[1, 3], padding=2, are_continuous=False, expected_result="01E03"),
    Case(id="non-continuous without prefix joins on ampersand", format_=_PLAIN,
         episode_numbers=[1, 3], padding=2, are_continuous=False, expected_result="01 & 03"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__get_episode_number_string(case: Case):
    result = _get_episode_number_string(format_=case.format_, episode_numbers=case.episode_numbers,
                                        episode_number_padding=case.padding, are_continuous=case.are_continuous)
    assert result == case.expected_result
