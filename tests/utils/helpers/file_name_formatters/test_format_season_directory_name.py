from dataclasses import dataclass

import pytest

from dto.orm_models import TrackedAnimeProcessingSettings
from utils.helpers.file_name_formatters import format_season_directory_name


def make_settings(*, fmt="Season {season_number}", padding=2):
    return TrackedAnimeProcessingSettings(season_directory_name_format=fmt,
                                          season_directory_number_padding=padding)


@dataclass
class Case:
    id: str
    season_number: int
    fmt: str = "Season {season_number}"
    padding: int = 2
    expected_result: str = ""


CASES = [
    Case(id="substituted and padded", season_number=3, padding=2, expected_result="Season 03"),
    Case(id="padding wider than number", season_number=12, fmt="S{season_number}", padding=3,
         expected_result="S012"),
    Case(id="number longer than padding is not truncated", season_number=100, padding=2,
         expected_result="Season 100"),
    Case(id="result is path cleaned", season_number=1, fmt="Season:{season_number}", padding=1,
         expected_result="Season꞉1"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_format_season_directory_name(case: Case):
    settings = make_settings(fmt=case.fmt, padding=case.padding)
    assert format_season_directory_name(settings, case.season_number) == case.expected_result
