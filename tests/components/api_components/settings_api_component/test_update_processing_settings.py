from dataclasses import dataclass

import pytest

from config import config
from api.schemas.settings_schemas import ProcessingSettings


@dataclass
class Case:
    id: str


CASES = [
    Case(id="persists and returns processing section"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_processing_settings(case: Case, bound_session, settings_api):
    us = config.user_settings
    expected_flag = not us.tvdb_structure_enabled_default
    # reuse current (valid) format strings so only the toggle changes; avoids format-token validation noise.
    body = ProcessingSettings(
        default_destination_directory=None,
        default_show_directory_name_format=us.default_show_directory_name_format,
        default_season_directory_name_format=us.default_season_directory_name_format,
        default_raw_episode_file_name_format=us.default_raw_episode_file_name_format,
        default_episode_file_name_format=us.default_episode_file_name_format,
        default_titleless_episode_file_name_format=us.default_titleless_episode_file_name_format,
        tvdb_structure_enabled_default=expected_flag,
    )
    result = await settings_api.update_processing_settings(body)

    assert config.user_settings.tvdb_structure_enabled_default == expected_flag
    assert result.tvdb_structure_enabled_default == expected_flag
    assert result.default_show_directory_name_format == us.default_show_directory_name_format
