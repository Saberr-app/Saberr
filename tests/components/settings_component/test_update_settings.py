from dataclasses import dataclass

import pytest

from common.exceptions import InvalidSettingValueException
from components.settings_component import SettingsComponent
from config import config
from constants import SettingsCode, AnilistTitleLanguage


@dataclass
class Case:
    id: str
    check: str
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="persists value to config", check="persists"),
    Case(id="enum setting round trips", check="enum_round_trip"),
    Case(id="unchanged first field does not block rest of batch", check="batch_continue"),
    Case(id="invalid value raises", check="invalid",
         expected_exception=InvalidSettingValueException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_settings(case: Case, mocker):
    repo_update = mocker.patch("repositories.settings_repo.SettingsRepo.update_setting")
    mocker.patch("repositories.audit_log_repo.AuditLogRepo.create_audit_log")

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await SettingsComponent().update_settings({SettingsCode.RSS_CHECK_FREQUENCY: 5})  # below minimum of 30
        repo_update.assert_not_awaited()
        return

    if case.check == "persists":
        await SettingsComponent().update_settings({SettingsCode.RSS_CHECK_FREQUENCY: 1234})
        assert config.user_settings.rss_check_frequency == 1234
        repo_update.assert_awaited_once_with(SettingsCode.RSS_CHECK_FREQUENCY, data=1234)
    elif case.check == "enum_round_trip":
        current = config.user_settings.anilist_preferred_title_language
        new = (AnilistTitleLanguage.ENGLISH if current != AnilistTitleLanguage.ENGLISH
               else AnilistTitleLanguage.NATIVE)
        await SettingsComponent().update_settings({SettingsCode.ANILIST_PREFERRED_TITLE_LANGUAGE: new})
        assert config.user_settings.anilist_preferred_title_language is new  # enum kept in memory
        repo_update.assert_awaited_once_with(SettingsCode.ANILIST_PREFERRED_TITLE_LANGUAGE, data=new)
    else:
        # regression guard: an unchanged field must `continue`, not `return`, so later fields still apply.
        await SettingsComponent().update_settings({
            SettingsCode.TIMEZONE: config.user_settings.timezone,   # unchanged -> skipped
            SettingsCode.RSS_CHECK_FREQUENCY: 4321,                 # must still be applied
        })
        assert config.user_settings.rss_check_frequency == 4321
        repo_update.assert_awaited_once_with(SettingsCode.RSS_CHECK_FREQUENCY, data=4321)
