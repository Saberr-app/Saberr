from dataclasses import dataclass
from datetime import datetime, UTC
from unittest.mock import AsyncMock

import pytest

from common.exceptions import NotFoundException, QbitNotConfiguredException
from components.api_components.tracked_anime_api_component import TrackedAnimeAPIComponent
from constants import Encoding, Resolution, TorrentDownloadStatus, VideoSource
from dto.orm_models import Torrent, TorrentDownload, TrackedAnimeEpisode
from dto.qbit import QBitTorrent
from api.schemas.tracked_anime_schemas import TrackedAnimeItemEpisode

_TA = "components.operational_components.tracked_anime_component.TrackedAnimeComponent"
_ANILIST = "components.service_components.anilist_component.AnilistComponent"
_QBIT = "components.service_components.qbit_component.QBitComponent"
_COMPONENT = "components.api_components.tracked_anime_api_component.TrackedAnimeAPIComponent"

_MAGNET = "hashA"


def _nyaa_xml() -> str:
    return (
        '<item xmlns:nyaa="https://nyaa.si/xmlns/nyaa">'
        '<title>[GroupA] Show - 01</title>'
        '<link>magnet:?xt=urn:btih:abc</link>'
        '<guid>https://nyaa.si/view/1</guid>'
        '<nyaa:seeders>10</nyaa:seeders>'
        '<nyaa:leechers>2</nyaa:leechers>'
        '<nyaa:downloads>100</nyaa:downloads>'
        f'<nyaa:infoHash>{_MAGNET}</nyaa:infoHash>'
        '<nyaa:categoryId>1_2</nyaa:categoryId>'
        '<nyaa:category>Anime</nyaa:category>'
        '<nyaa:size>1.0 GiB</nyaa:size>'
        '<nyaa:comments>0</nyaa:comments>'
        '<nyaa:remake>No</nyaa:remake>'
        '<nyaa:trusted>Yes</nyaa:trusted>'
        '<description>some description</description>'
        '<pubDate>Mon, 01 Jan 2024 00:00:00 +0000</pubDate>'
        '</item>'
    )


def _episode_with_torrent(episode_number: int) -> TrackedAnimeEpisode:
    download = TorrentDownload(torrent_id=None, status=TorrentDownloadStatus.PROCESSED,
                              download_directory_path="/staging", destination_path="/dest",
                              status_details=None, status_retry_count=0)
    download.id = 501
    download.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    download.copied_to_destination_path_at = None
    torrent = Torrent(tracked_anime_episode_id=None, magnet_hash=_MAGNET, rss_xml=_nyaa_xml(),
                      torrent_link="magnet:?xt=urn:btih:abc", torrent_title="[GroupA] Show - 01",
                      release_group="GroupA", title="Show", episode_number=episode_number, episode_part=0,
                      episode_part_ceiling=0, language_code="eng", encoding=Encoding.HEVC,
                      resolution=Resolution.P1080, source=VideoSource.CRUNCHYROLL)
    torrent.id = 401
    torrent.parent_torrent_id = None
    torrent.version_number = 1
    torrent.repack_indicator = False
    torrent.download = download
    download.torrent = torrent
    episode = TrackedAnimeEpisode(tracked_anime_id=None, episode_number=episode_number,
                                  tvdb_episode_ids=[], tvdb_episode_numbers=[])
    episode.id = 301
    episode.torrents = [torrent]
    return episode


def _episode_item(episode_number: int) -> TrackedAnimeItemEpisode:
    return TrackedAnimeItemEpisode(
        episode_number=episode_number, tvdb_series_episodes=[], tvdb_episode_part=None,
        tvdb_episode_part_ceiling=None, auto_discard=False, download_id=501,
        download_status=TorrentDownloadStatus.PROCESSED)


@dataclass
class Case:
    id: str
    flow: str  # "tracked_missing" | "episode_missing" | "no_torrents" | "with_qbit" | "qbit_unconfigured"


CASES = [
    Case(id="missing tracked anime raises", flow="tracked_missing"),
    Case(id="episode outside build window raises", flow="episode_missing"),
    Case(id="episode without torrents returns empty list", flow="no_torrents"),
    Case(id="merges qbit progress into download", flow="with_qbit"),
    Case(id="qbit not configured leaves qbit fields empty", flow="qbit_unconfigured"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_tracked_anime_episode_details(case: Case, make_anime, make_full_tracked_anime, mocker):
    component = TrackedAnimeAPIComponent()
    episode_number = 1
    tracked = make_full_tracked_anime(anilist_id=8731)
    anime = make_anime(anilist_id=8731)

    if case.flow == "with_qbit" or case.flow == "qbit_unconfigured":
        tracked.episodes = [_episode_with_torrent(episode_number)]
    built = [] if case.flow == "episode_missing" else [_episode_item(episode_number)]

    mocker.patch(f"{_TA}.get_tracked_anime_by_id",
                 return_value=None if case.flow == "tracked_missing" else tracked)
    mocker.patch(f"{_ANILIST}.get_anime", return_value=anime)
    mocker.patch(f"{_COMPONENT}._build_episodes", new=AsyncMock(return_value=built))
    if case.flow == "qbit_unconfigured":
        mocker.patch(f"{_QBIT}.get_torrents", side_effect=QbitNotConfiguredException("nope"))
    else:
        qbit_item = QBitTorrent(amount_left=0, eta=120, hash=_MAGNET, name="n", progress=0.5,
                                save_path="/dl", content_path="/dl/n", state="downloading", size=1,
                                original_save_path="/dl", original_content_path="/dl/n")
        mocker.patch(f"{_QBIT}.get_torrents", return_value=[qbit_item])

    if case.flow in ("tracked_missing", "episode_missing"):
        with pytest.raises(NotFoundException):
            await component.get_tracked_anime_episode_details(
                tracked_anime_id=tracked.id, episode_number=episode_number, force_freshness=False)
        return

    result = await component.get_tracked_anime_episode_details(
        tracked_anime_id=tracked.id, episode_number=episode_number, force_freshness=False)

    assert result.episode_number == episode_number
    if case.flow == "no_torrents":
        assert result.torrents == []
        return

    assert len(result.torrents) == 1
    torrent_item = result.torrents[0]
    assert torrent_item.parent_id == 401
    assert torrent_item.children_ids == []
    assert torrent_item.download.id == 501
    if case.flow == "with_qbit":
        assert torrent_item.download.qbit_status == "downloading"
        assert torrent_item.download.qbit_progress == 0.5
        assert torrent_item.download.qbit_eta == 120
    else:
        assert torrent_item.download.qbit_status is None
        assert torrent_item.download.qbit_progress is None
