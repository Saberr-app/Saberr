from dataclasses import dataclass
from typing import Any

import pytest

from common.exceptions import InvalidSettingValueException
from components.settings_component import SettingsComponent
from constants import SettingsCode, AnilistTitleLanguage, RSSCategory, ProxyProtocol
from dto.proxy_config import ProxyConfig

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
    Case(id="daily missing report accepts bool", code=SettingsCode.DISCORD_SEND_DAILY_MISSING_REPORT, value=True),
    Case(id="daily missing report rejects none", code=SettingsCode.DISCORD_SEND_DAILY_MISSING_REPORT, value=None,
         expected_exception=InvalidSettingValueException),
    Case(id="daily missing report rejects non-bool", code=SettingsCode.DISCORD_SEND_DAILY_MISSING_REPORT,
         value="yes", expected_exception=InvalidSettingValueException),
    Case(id="discord notify flags reject none", code=SettingsCode.DISCORD_NOTIFY_ON_DOWNLOAD_FAILED, value=None,
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
    Case(id="proxy http without credentials is coerced to dto",
         code=SettingsCode.RSS_PROXY_CONFIG, value="http://1.2.3.4:3128",
         expected_result=ProxyConfig(host="1.2.3.4", port=3128, username=None, password=None,
                                     protocol=ProxyProtocol.HTTP)),
    Case(id="proxy socks5 with credentials is coerced to dto",
         code=SettingsCode.RSS_PROXY_CONFIG, value="socks5://u:p@1.2.3.4:1080",
         expected_result=ProxyConfig(host="1.2.3.4", port=1080, username="u", password="p",
                                     protocol=ProxyProtocol.SOCKS5)),
    Case(id="proxy percent escapes are decoded",
         code=SettingsCode.RSS_PROXY_CONFIG, value="http://u:p%40s%3As@1.2.3.4:3128",
         expected_result=ProxyConfig(host="1.2.3.4", port=3128, username="u", password="p@s:s",
                                     protocol=ProxyProtocol.HTTP)),
    Case(id="proxy socks4 allows username without password",
         code=SettingsCode.RSS_PROXY_CONFIG, value="socks4://user@1.2.3.4:1080",
         expected_result=ProxyConfig(host="1.2.3.4", port=1080, username="user", password=None,
                                     protocol=ProxyProtocol.SOCKS4)),
    Case(id="proxy nullable allows none", code=SettingsCode.RSS_PROXY_CONFIG, value=None),
    Case(id="proxy without host raises",
         code=SettingsCode.RSS_PROXY_CONFIG, value="http://:3128",
         expected_exception=InvalidSettingValueException),
    Case(id="proxy without port raises",
         code=SettingsCode.RSS_PROXY_CONFIG, value="http://1.2.3.4",
         expected_exception=InvalidSettingValueException),
    Case(id="proxy with password but no username raises",
         code=SettingsCode.RSS_PROXY_CONFIG, value="http://:p@1.2.3.4:3128",
         expected_exception=InvalidSettingValueException),
    Case(id="proxy with username but no password raises",
         code=SettingsCode.RSS_PROXY_CONFIG, value="http://u@1.2.3.4:3128",
         expected_exception=InvalidSettingValueException),
    Case(id="proxy with unsupported scheme raises",
         code=SettingsCode.RSS_PROXY_CONFIG, value="ftp://1.2.3.4:21",
         expected_exception=InvalidSettingValueException),
    Case(id="proxy garbage raises",
         code=SettingsCode.RSS_PROXY_CONFIG, value="garbage",
         expected_exception=InvalidSettingValueException),
    Case(id="proxy torrent files flag accepts bool",
         code=SettingsCode.RSS_PROXY_TORRENT_FILES_ENABLED, value=True, expected_result=True),
    Case(id="proxy torrent files flag rejects non-bool",
         code=SettingsCode.RSS_PROXY_TORRENT_FILES_ENABLED, value="yes",
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
        assert result == case.expected_result
