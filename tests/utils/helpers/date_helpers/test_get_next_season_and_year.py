from dataclasses import dataclass
from datetime import datetime, UTC

import pytest

from constants import AnilistAnimeSeason
from utils.helpers import date_helpers
from utils.helpers.date_helpers import get_next_season_and_year


@dataclass
class Case:
    id: str
    month: int                       # drives the current season
    expected_season: AnilistAnimeSeason
    expected_year: int


CASES = [
    # fall rolls over into next year's winter
    Case(id="fall -> winter next year", month=11, expected_season=AnilistAnimeSeason.WINTER,
         expected_year=2025),
    Case(id="winter -> spring same year", month=1, expected_season=AnilistAnimeSeason.SPRING,
         expected_year=2024),
    Case(id="spring -> summer same year", month=5, expected_season=AnilistAnimeSeason.SUMMER,
         expected_year=2024),
    Case(id="summer -> fall same year", month=8, expected_season=AnilistAnimeSeason.FALL,
         expected_year=2024),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_get_next_season_and_year(case: Case, mocker):
    frozen = datetime(2024, case.month, 15, tzinfo=UTC)
    mocker.patch.object(date_helpers, "datetime").now.return_value = frozen

    season, year = get_next_season_and_year()

    assert season == case.expected_season
    assert year == case.expected_year
