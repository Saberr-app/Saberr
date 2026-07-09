from dataclasses import dataclass

import pytest

from components.settings_component import SettingsComponent
from config import config
from constants import SettingsCode


@dataclass
class Case:
    id: str
    check: str  # which assertion path to run


CASES = [
    Case(id="returns settings dict keyed by code", check="keyed_by_code"),
    Case(id="token is masked", check="token_masked"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_settings(case: Case, bound_session):
    result = await SettingsComponent().get_settings()

    if case.check == "keyed_by_code":
        assert result[SettingsCode.TIMEZONE.value] == config.user_settings.timezone
        assert result[SettingsCode.RSS_CHECK_FREQUENCY.value] == config.user_settings.rss_check_frequency
    else:
        assert result[SettingsCode.ANILIST_USER_TOKEN.value] in ("SET", "UNSET")
        expected = "SET" if config.user_settings.anilist_user_token is not None else "UNSET"
        assert result[SettingsCode.ANILIST_USER_TOKEN.value] == expected
