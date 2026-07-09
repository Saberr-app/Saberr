from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Callable

import pytest

from config import config
from utils.helpers.discord_webhook_helpers import construct_discord_webhook_payload_for_processing_finished

_WHEN = datetime(2021, 1, 1, tzinfo=UTC)
_X = "⨯"  # the season/episode separator used in the TVDB Episode field


def processing_kwargs(**overrides):
    base = dict(
        anime_title="My Anime",
        anilist_id=123,
        mal_id=456,
        nyaa_id="789",
        tvdb_series_id=111,
        season_number=1,
        anime_episode_number=5,
        tvdb_episode_numbers=[5],
        tvdb_episode_part=None,
        tvdb_episode_title="Episode Title",
        tvdb_episode_overview="An overview.",
        destination_path="/anime/My Anime/Season 01/ep.mkv",
        release_group="SubsPlease",
        release_title="[SubsPlease] My Anime - 05 (1080p).mkv",
        file_size_bytes=1024 ** 3,
        file_extension="mkv",
        resolution="1080p",
        encoding="HEVC",
        resolved_audio_languages=["jp"],
        resolved_duration_seconds=1440,
        resolved_source="Crunchyroll",
        is_an_upgrade=False,
        poster_url="http://img/poster.jpg",
        episode_image_url="http://img/ep.jpg",
        banner_url="http://img/banner.jpg",
        anilist_rating=85,
        time=_WHEN,
    )
    base.update(overrides)
    return base


def build(**overrides):
    return construct_discord_webhook_payload_for_processing_finished(**processing_kwargs(**overrides))


def embed_of(payload):
    return payload["embeds"][0]


def field_value(payload, name):
    return next(f["value"] for f in embed_of(payload)["fields"] if f["name"] == name)


@dataclass
class Case:
    id: str
    kwargs: dict = field(default_factory=dict)
    published_url: str | None = None
    check: Callable[[dict], None] = lambda payload: None


def _returns_single_embed(payload):
    assert list(payload.keys()) == ["embeds"]
    assert len(payload["embeds"]) == 1


def _title_has_padded_episode(payload):
    assert embed_of(payload)["title"] == "My Anime - E05"


def _no_url_without_published_url(payload):
    assert "url" not in embed_of(payload)


def _url_points_to_anime_page(payload):
    assert embed_of(payload)["url"] == "http://host/browse?anilist_id=123"


def _new_release_styling(payload):
    embed = embed_of(payload)
    assert embed["description"] == "New release."
    assert embed["color"] == 0x4BA049


def _upgrade_styling(payload):
    embed = embed_of(payload)
    assert embed["description"] == "Upgraded release."
    assert embed["color"] == 0x304EB6


def _specs_human_readable(payload):
    specs = field_value(payload, "Specs")
    assert "1.00 GB" in specs
    assert "24m" in specs  # 1440s


def _overview_present_and_shortened(payload):
    overview = field_value(payload, "Overview")
    assert len(overview) == 500 and overview.endswith("...")


def _overview_absent(payload):
    names = [f["name"] for f in embed_of(payload)["fields"]]
    assert "Overview" not in names


def _rating_footer(payload):
    assert embed_of(payload)["footer"]["text"] == "Anilist rating: 8.5/10"


def _no_footer(payload):
    assert "footer" not in embed_of(payload)


def _poster_thumbnail(payload):
    assert embed_of(payload)["thumbnail"] == {"url": "http://img/p.jpg"}


def _episode_image_preferred(payload):
    assert embed_of(payload)["image"] == {"url": "http://img/ep.jpg"}


def _banner_used(payload):
    assert embed_of(payload)["image"] == {"url": "http://img/b.jpg"}


def _assert_tvdb_episode(payload, expected):
    assert field_value(payload, "TVDB Episode") == expected


def _assert_in(needle, haystack):
    assert needle in haystack


def _assert_not_in(needle, haystack):
    assert needle not in haystack


CASES = [
    Case(id="returns single embed", check=_returns_single_embed),
    Case(id="title carries the zero-padded episode", check=_title_has_padded_episode),
    Case(id="no url without a published url", check=_no_url_without_published_url),
    Case(id="url points to the anime page", published_url="http://host/", check=_url_points_to_anime_page),
    Case(id="new release styling", kwargs=dict(is_an_upgrade=False), check=_new_release_styling),
    Case(id="upgrade styling", kwargs=dict(is_an_upgrade=True), check=_upgrade_styling),
    Case(id="episode field uses the anime episode number",
         check=lambda p: _assert_in("Episode 5", field_value(p, "Episode"))),
    Case(id="single tvdb episode formatting", kwargs=dict(tvdb_episode_numbers=[5]),
         check=lambda p: _assert_tvdb_episode(p, f"Season 1 {_X} Episode 5 - Episode Title")),
    Case(id="multiple tvdb episode formatting", kwargs=dict(tvdb_episode_numbers=[5, 6]),
         check=lambda p: _assert_tvdb_episode(p, f"Season 1 {_X} Episode 5-6 - Episode Title")),
    Case(id="tvdb episode part is appended", kwargs=dict(tvdb_episode_numbers=[5], tvdb_episode_part=2),
         check=lambda p: _assert_tvdb_episode(p, f"Season 1 {_X} Episode 5 Part 2 - Episode Title")),
    Case(id="empty tvdb episode field without tvdb numbers", kwargs=dict(tvdb_episode_numbers=[]),
         check=lambda p: _assert_tvdb_episode(p, "")),
    Case(id="specs include human readable size and duration",
         kwargs=dict(file_size_bytes=1024 ** 3, resolved_duration_seconds=1440),
         check=_specs_human_readable),
    Case(id="links include optional services when present", kwargs=dict(tvdb_series_id=111),
         check=lambda p: _assert_in("TheTVDB", field_value(p, "Links"))),
    Case(id="links omit optional services when absent", kwargs=dict(tvdb_series_id=None),
         check=lambda p: _assert_not_in("TheTVDB", field_value(p, "Links"))),
    Case(id="overview field present and shortened", kwargs=dict(tvdb_episode_overview="x" * 600),
         check=_overview_present_and_shortened),
    Case(id="overview field absent when no overview", kwargs=dict(tvdb_episode_overview=None),
         check=_overview_absent),
    Case(id="rating footer", kwargs=dict(anilist_rating=85), check=_rating_footer),
    Case(id="no footer without rating", kwargs=dict(anilist_rating=None), check=_no_footer),
    Case(id="poster becomes thumbnail", kwargs=dict(poster_url="http://img/p.jpg"),
         check=_poster_thumbnail),
    Case(id="episode image preferred over banner",
         kwargs=dict(episode_image_url="http://img/ep.jpg", banner_url="http://img/b.jpg"),
         check=_episode_image_preferred),
    Case(id="banner used when no episode image",
         kwargs=dict(episode_image_url=None, banner_url="http://img/b.jpg"),
         check=_banner_used),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_construct_discord_webhook_payload_for_processing_finished(case: Case):
    if case.published_url is not None:
        config.user_settings.published_url = case.published_url
    case.check(build(**case.kwargs))
