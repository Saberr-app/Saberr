from dataclasses import dataclass

import pytest

from config import config
from api.schemas.settings_schemas import RSSSettings
from constants import RSSCategory


@dataclass
class Case:
    id: str
    body: RSSSettings


CASES = [
    Case(id="persists and returns rss section",
         body=RSSSettings(auto_download=False, rss_check_frequency=900, rss_category=RSSCategory.ENGLISH_TRANSLATED)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_rss_settings(case: Case, bound_session, settings_api):
    result = await settings_api.update_rss_settings(case.body)
    assert config.user_settings.auto_download is False
    assert config.user_settings.rss_check_frequency == 900
    assert config.user_settings.rss_category == RSSCategory.ENGLISH_TRANSLATED
    assert result.auto_download is False
    assert result.rss_check_frequency == 900
    assert result.rss_category == RSSCategory.ENGLISH_TRANSLATED
