from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from config import config
from api.schemas.settings_schemas import QBitServiceSettings


@dataclass
class Case:
    id: str
    staging_directory: str | None
    expected_staging_directory: str | None


CASES = [
    Case(id="persists and returns service section",
         staging_directory=None,
         expected_staging_directory=None),
    Case(id="keeps windows staging path intact",
         staging_directory="C:\\Users\\hasan\\Downloads\\qBit\\",
         expected_staging_directory="C:\\Users\\hasan\\Downloads\\qBit\\"),
    Case(id="keeps posix staging path intact",
         staging_directory="/mnt/downloads/qbit",
         expected_staging_directory="/mnt/downloads/qbit"),
    Case(id="strips trailing dots and spaces from staging path",
         staging_directory="  C:\\Downloads\\staging. . ",
         expected_staging_directory="C:\\Downloads\\staging"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_qbit_service_settings(case: Case, bound_session, settings_api, monkeypatch):
    # the update triggers a real qBit healthcheck; stub it out so no network call happens.
    from app_state import downstream_healthcheck_workers
    monkeypatch.setattr(downstream_healthcheck_workers, "_check_qbit", AsyncMock())

    body = QBitServiceSettings(qbit_base_url="http://localhost:8080",
                               qbit_username="user",
                               qbit_password="pass",
                               qbit_remote_path_mapping_remote_path=None,
                               qbit_remote_path_mapping_local_path=None,
                               torrent_category="anime",
                               staging_directory=case.staging_directory,
                               organize_downloads=False,
                               apply_release_group_as_torrent_tag=True,
                               apply_encoding_as_torrent_tag=False,
                               apply_resolution_as_torrent_tag=True,
                               apply_language_code_as_torrent_tag=False,
                               apply_anime_title_as_torrent_tag=True,)

    result = await settings_api.update_qbit_service_settings(body)

    assert config.user_settings.qbit_base_url == "http://localhost:8080"
    assert config.user_settings.qbit_username == "user"
    assert config.user_settings.qbit_password == "pass"

    assert config.user_settings.torrent_category == "anime"
    assert config.user_settings.organize_downloads is False
    assert config.user_settings.apply_resolution_as_torrent_tag is True
    assert config.user_settings.staging_directory == case.expected_staging_directory

    assert result.torrent_category == "anime"
    assert result.organize_downloads is False
    assert result.apply_release_group_as_torrent_tag is True
    assert result.apply_encoding_as_torrent_tag is False
    assert result.staging_directory == case.expected_staging_directory

    assert result.qbit_base_url == "http://localhost:8080"
    assert result.qbit_username == "user"
    # the password is masked in the response once set
    assert result.qbit_password == "SET"
