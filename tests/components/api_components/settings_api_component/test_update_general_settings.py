from dataclasses import dataclass

import pytest

from config import config
from constants import AnilistTitleLanguage
from api.schemas.settings_schemas import GeneralSettings


@dataclass
class Case:
    id: str


CASES = [
    Case(id="persists and returns general section"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_general_settings(case: Case, bound_session, settings_api):
    current = config.user_settings.anilist_preferred_title_language
    new_lang = (AnilistTitleLanguage.ENGLISH if current != AnilistTitleLanguage.ENGLISH
                else AnilistTitleLanguage.NATIVE)
    body = GeneralSettings(
        set_download_as_failed_after_minutes=42,
        set_processing_as_failed_after_minutes=7,
        timezone="Asia/Tokyo",
        published_url=None,
        anilist_preferred_title_language=new_lang,
    )
    result = await settings_api.update_general_settings(body)

    assert config.user_settings.set_download_as_failed_after_minutes == 42
    assert config.user_settings.set_processing_as_failed_after_minutes == 7
    assert config.user_settings.timezone == "Asia/Tokyo"
    # title language now round-trips: stored as its .value, kept as the enum in memory.
    assert config.user_settings.anilist_preferred_title_language is new_lang

    assert result.set_download_as_failed_after_minutes == 42
    assert result.timezone == "Asia/Tokyo"
    assert result.anilist_preferred_title_language is new_lang
