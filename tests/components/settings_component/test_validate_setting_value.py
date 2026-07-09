from dataclasses import dataclass
from typing import Any

import pytest

from common.exceptions import InvalidSettingValueException
from components.settings_component import SettingsComponent
from constants import SettingsCode, AnilistTitleLanguage, RSSCategory

validate = SettingsComponent.validate_setting_value


@dataclass
class Case:
    id: str
    code: SettingsCode
    value: Any
    expected_result: Any = None
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="valid url passes", code=SettingsCode.PUBLISHED_URL, value="https://example.com"),
    Case(id="invalid url raises", code=SettingsCode.PUBLISHED_URL, value="not a url",
         expected_exception=InvalidSettingValueException),
    Case(id="nullable url allows none", code=SettingsCode.PUBLISHED_URL, value=None),
    Case(id="valid timezone passes", code=SettingsCode.TIMEZONE, value="UTC"),
    Case(id="invalid timezone raises", code=SettingsCode.TIMEZONE, value="Mars/Phobos",
         expected_exception=InvalidSettingValueException),
    Case(id="int below minimum raises", code=SettingsCode.RSS_CHECK_FREQUENCY, value=5,  # minimum is 30
         expected_exception=InvalidSettingValueException),
    Case(id="digit string accepts digits", code=SettingsCode.DISCORD_USER_ID, value="123456789"),
    Case(id="digit string rejects non-digits", code=SettingsCode.DISCORD_USER_ID, value="abc",
         expected_exception=InvalidSettingValueException),
    Case(id="title language is coerced to enum",
         code=SettingsCode.ANILIST_PREFERRED_TITLE_LANGUAGE, value="English",
         expected_result=AnilistTitleLanguage.ENGLISH),
    Case(id="invalid title language raises",
         code=SettingsCode.ANILIST_PREFERRED_TITLE_LANGUAGE, value="Klingon",
         expected_exception=InvalidSettingValueException),
    Case(id="rss category is coerced to enum",
         code=SettingsCode.RSS_CATEGORY, value="English Translated",
         expected_result=RSSCategory.ENGLISH_TRANSLATED),
    Case(id="invalid category raises",
         code=SettingsCode.RSS_CATEGORY, value="Not a category",
         expected_exception=InvalidSettingValueException),
    Case(id="valid format tokens pass",
         code=SettingsCode.DEFAULT_SHOW_DIRECTORY_NAME_FORMAT, value="{anilist_title_english}"),
    Case(id="invalid format tokens raise",
         code=SettingsCode.DEFAULT_SHOW_DIRECTORY_NAME_FORMAT, value="{nonexistent_token}",
         expected_exception=InvalidSettingValueException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_validate_setting_value(case: Case):
    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            validate(case.code, case.value)
        return

    result = validate(case.code, case.value)
    if case.expected_result is not None:
        assert result is case.expected_result
