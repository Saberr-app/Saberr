from dataclasses import dataclass
from datetime import datetime, UTC

import pytest

from constants import AnilistAnimeSeason
from utils.helpers import date_helpers
from utils.helpers.date_helpers import get_current_season_and_year


@dataclass
class Case:
    id: str
    month: int
    expected_season: AnilistAnimeSeason


CASES = [
    Case(id="january is winter", month=1, expected_season=AnilistAnimeSeason.WINTER),
    Case(id="march is winter", month=3, expected_season=AnilistAnimeSeason.WINTER),
    Case(id="april is spring", month=4, expected_season=AnilistAnimeSeason.SPRING),
    Case(id="june is spring", month=6, expected_season=AnilistAnimeSeason.SPRING),
    Case(id="july is summer", month=7, expected_season=AnilistAnimeSeason.SUMMER),
    Case(id="september is summer", month=9, expected_season=AnilistAnimeSeason.SUMMER),
    Case(id="october is fall", month=10, expected_season=AnilistAnimeSeason.FALL),
    Case(id="december is fall", month=12, expected_season=AnilistAnimeSeason.FALL),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_get_current_season_and_year(case: Case, mocker):
    frozen = datetime(2024, case.month, 15, tzinfo=UTC)
    mocker.patch.object(date_helpers, "datetime").now.return_value = frozen

    season, year = get_current_season_and_year()

    assert season == case.expected_season
    assert year == 2024
