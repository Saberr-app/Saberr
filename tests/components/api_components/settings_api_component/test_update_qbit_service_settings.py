from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from config import config
from api.schemas.settings_schemas import QBitServiceSettings


@dataclass
class Case:
    id: str
    body: QBitServiceSettings


CASES = [
    Case(id="persists and returns service section",
         body=QBitServiceSettings(qbit_base_url="http://localhost:8080",
                                  qbit_username="user",
                                  qbit_password="pass",
                                  qbit_remote_path_mapping_remote_path=None,
                                  qbit_remote_path_mapping_local_path=None,
                                  torrent_category="anime",
                                  staging_directory=None,
                                  organize_downloads=False,
                                  apply_release_group_as_torrent_tag=True,
                                  apply_encoding_as_torrent_tag=False,
                                  apply_resolution_as_torrent_tag=True,
                                  apply_language_code_as_torrent_tag=False,
                                  apply_anime_title_as_torrent_tag=True,)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_qbit_service_settings(case: Case, bound_session, settings_api, monkeypatch):
    # the update triggers a real qBit healthcheck; stub it out so no network call happens.
    from app_state import downstream_healthcheck_workers
    monkeypatch.setattr(downstream_healthcheck_workers, "_check_qbit", AsyncMock())

    result = await settings_api.update_qbit_service_settings(case.body)

    assert config.user_settings.qbit_base_url == "http://localhost:8080"
    assert config.user_settings.qbit_username == "user"
    assert config.user_settings.qbit_password == "pass"

    assert config.user_settings.torrent_category == "anime"
    assert config.user_settings.organize_downloads is False
    assert config.user_settings.apply_resolution_as_torrent_tag is True

    assert result.torrent_category == "anime"
    assert result.organize_downloads is False
    assert result.apply_release_group_as_torrent_tag is True
    assert result.apply_encoding_as_torrent_tag is False

    assert result.qbit_base_url == "http://localhost:8080"
    assert result.qbit_username == "user"
    # the password is masked in the response once set
    assert result.qbit_password == "SET"
