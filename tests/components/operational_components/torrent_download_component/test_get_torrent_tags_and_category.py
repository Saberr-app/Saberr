from dataclasses import dataclass

import pytest

from components.operational_components.torrent_download_component import TorrentDownloadComponent
from config import config
from constants import Encoding, Resolution
from dto.orm_models import Torrent, TrackedAnime, TrackedAnimeEpisode

get_tags = TorrentDownloadComponent.get_torrent_tags_and_category

_TAG_FLAGS = ("apply_anime_title_as_torrent_tag", "apply_release_group_as_torrent_tag",
              "apply_encoding_as_torrent_tag", "apply_resolution_as_torrent_tag",
              "apply_language_code_as_torrent_tag")


def _torrent(*, release_group="GroupA", encoding=Encoding.HEVC, resolution=Resolution.P1080,
             language_code="eng", title="My Show"):
    anime = TrackedAnime(romaji_title=title)
    episode = TrackedAnimeEpisode()
    episode.tracked_anime = anime
    torrent = Torrent()
    torrent.tracked_anime_episode = episode
    torrent.release_group = release_group
    torrent.encoding = encoding
    torrent.resolution = resolution
    torrent.language_code = language_code
    return torrent


@dataclass
class Case:
    id: str
    tag_flags: bool
    torrent_category: str
    torrent_kwargs: dict
    expected_tags: list[str]
    expected_category: str | None


CASES = [
    Case(id="all flags on collects every tag in order", tag_flags=True, torrent_category="anime",
         torrent_kwargs={}, expected_tags=["My Show", "GroupA", "HEVC", "1080p", "eng"],
         expected_category="anime"),
    Case(id="all flags off yields no tags", tag_flags=False, torrent_category="",
         torrent_kwargs={}, expected_tags=[], expected_category=None),
    Case(id="optional fields skipped when none even with flags on", tag_flags=True,
         torrent_category="anime",
         torrent_kwargs=dict(encoding=None, resolution=None, language_code=None),
         expected_tags=["My Show", "GroupA"], expected_category="anime"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_torrent_tags_and_category(case: Case, monkeypatch):
    for flag in _TAG_FLAGS:
        monkeypatch.setattr(config.user_settings, flag, case.tag_flags)
    monkeypatch.setattr(config.user_settings, "torrent_category", case.torrent_category)

    tags, category = await get_tags(_torrent(**case.torrent_kwargs))

    assert tags == case.expected_tags
    assert category == case.expected_category
