from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from components.api_components.settings_api_component import SettingsAPIComponent
from constants import SettingsCode

_SETTINGS = "components.settings_component.SettingsComponent"
_LIST = "components.service_components.anilist_list_component.AnilistListComponent"


@dataclass
class Case:
    id: str


CASES = [
    Case(id="clears anilist settings and deletes the cached user list"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_logout_from_anilist(case: Case, mocker):
    mocker.patch("components.api_components.settings_api_component.create_task", new=MagicMock())
    mocker.patch("app_state.downstream_healthcheck_workers.force_check", new=MagicMock())
    update = mocker.patch(f"{_SETTINGS}.update_settings")
    delete = mocker.patch(f"{_LIST}.delete_user_anime_list")

    await SettingsAPIComponent().logout_from_anilist()

    update.assert_awaited_once_with({SettingsCode.ANILIST_USERNAME: None,
                                     SettingsCode.ANILIST_USER_TOKEN: None,
                                     SettingsCode.ANILIST_USER_DATA: None})
    delete.assert_awaited_once_with()
