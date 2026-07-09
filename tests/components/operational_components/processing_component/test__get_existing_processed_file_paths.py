from dataclasses import dataclass, field
from pathlib import Path

import pytest

from components.operational_components.processing_component import ProcessingComponent
from constants import TorrentDownloadStatus

get_paths = ProcessingComponent._get_existing_processed_file_paths
_REPO = "repositories.torrent_repositories.torrent_download_repo.TorrentDownloadRepo"


@dataclass
class Case:
    id: str
    destination_paths: list[str | None]  # destination_path of each processed download the repo returns
    expected_paths: list[Path] = field(default_factory=list)


CASES = [
    Case(id="returns resolved destination paths of processed downloads",
         destination_paths=["/library/a.mkv", None],  # the None one is skipped (no destination)
         expected_paths=[Path("/library/a.mkv").resolve()]),
    Case(id="returns empty when no processed downloads",
         destination_paths=[], expected_paths=[]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_existing_processed_file_paths(case: Case, make_torrent_download, mocker):
    downloads = [make_torrent_download(torrent_id=1, status=TorrentDownloadStatus.PROCESSED,
                                       destination_path=dest)
                 for dest in case.destination_paths]
    mocker.patch(f"{_REPO}.get_by_episode_id_and_part", return_value=downloads)

    paths = await get_paths(tracked_anime_episode_id=1, episode_part=0, episode_part_ceiling=0)

    assert paths == case.expected_paths
