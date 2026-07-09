from datetime import datetime, UTC, timedelta

from constants import AnilistAnimeSeason


def get_current_season_and_year() -> tuple[AnilistAnimeSeason, int]:
    current_date = datetime.now(UTC)
    if current_date.month < 4:
        return AnilistAnimeSeason.WINTER, current_date.year
    elif current_date.month < 7:
        return AnilistAnimeSeason.SPRING, current_date.year
    elif current_date.month < 10:
        return AnilistAnimeSeason.SUMMER, current_date.year
    else:
        return AnilistAnimeSeason.FALL, current_date.year


def get_next_season_and_year() -> tuple[AnilistAnimeSeason, int]:
    current_season, current_year = get_current_season_and_year()
    if current_season == AnilistAnimeSeason.FALL:
        return AnilistAnimeSeason.WINTER, current_year + 1
    elif current_season == AnilistAnimeSeason.WINTER:
        return AnilistAnimeSeason.SPRING, current_year
    elif current_season == AnilistAnimeSeason.SPRING:
        return AnilistAnimeSeason.SUMMER, current_year
    else:
        return AnilistAnimeSeason.FALL, current_year


def seconds_to_midnight() -> int:
    now = datetime.now(UTC)
    midnight = datetime(now.year, now.month, now.day, tzinfo=UTC) + timedelta(days=1)
    return int((midnight - now).total_seconds())
