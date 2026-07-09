from dataclasses import dataclass, field

import pytest

from components.api_components.settings_api_component import SettingsAPIComponent
from tests.support.builders import make_user_settings


@dataclass
class Case:
    id: str
    overrides: dict = field(default_factory=dict)


CASES = [
    Case(id="maps general fields from user settings",
         overrides=dict(timezone="Europe/Paris", published_url="http://host",
                        set_download_as_failed_after_minutes=90,
                        set_processing_as_failed_after_minutes=20)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__general_settings(case: Case):
    user_settings = make_user_settings(**case.overrides)
    component = SettingsAPIComponent.__new__(SettingsAPIComponent)

    section = component._general_settings(user_settings)

    assert section.timezone == user_settings.timezone
    assert section.published_url == user_settings.published_url
    assert section.set_download_as_failed_after_minutes == user_settings.set_download_as_failed_after_minutes
    assert section.set_processing_as_failed_after_minutes == user_settings.set_processing_as_failed_after_minutes
    assert section.anilist_preferred_title_language == user_settings.anilist_preferred_title_language
