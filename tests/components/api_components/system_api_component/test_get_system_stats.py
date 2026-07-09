from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

import pytest

from components.api_components.system_api_component import SystemAPIComponent
from config import config

_MODULE = "components.api_components.system_api_component"
_TA = "components.operational_components.tracked_anime_component.TrackedAnimeComponent"


@dataclass
class Case:
    id: str
    destination_directory: str
    staging_directory: str
    library_directory: str


CASES = [
    Case(id="aggregates library, import and downloads destinations into distinct disks",
         destination_directory="/dest", staging_directory="/staging", library_directory="/lib"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_system_stats(case: Case, mocker):
    config.user_settings.default_destination_directory = case.destination_directory
    config.user_settings.staging_directory = case.staging_directory
    mocker.patch(f"{_TA}.get_all_tracked_anime",
                 return_value=[SimpleNamespace(show_parent_directory=case.library_directory)])
    mocker.patch(f"{_MODULE}.get_up_since", return_value=datetime(2024, 1, 1))
    # each directory resolves to a distinct mount named after itself
    mocker.patch(f"{_MODULE}.get_disk_for_path", side_effect=lambda d: (d, 100, 40))

    stats = await SystemAPIComponent().get_system_stats()

    assert stats.app_version == config.app_version.original_version_string
    assert stats.up_since == datetime(2024, 1, 1)
    assert stats.update_available is False
    assert {disk.path for disk in stats.disk_stats} == {case.library_directory,
                                                         case.destination_directory,
                                                         case.staging_directory}
    staging = next(disk for disk in stats.disk_stats if disk.path == case.staging_directory)
    assert staging.name == "Torrent/downloads destination"
    assert staging.total == 100 and staging.used == 40
