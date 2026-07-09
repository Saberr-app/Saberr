from dataclasses import dataclass
from types import SimpleNamespace
from typing import Callable

import pytest

from constants import Encoding, Resolution, AnilistAnimeSeason, TVDBSeasonType
from common.exceptions import TorrentEpisodeCountMismatch
from dto.orm_models import Torrent, TrackedAnime, TrackedAnimeEpisode, TrackedAnimeProcessingSettings
from dto.tvdb import TVDBSeriesEpisode
from utils.helpers.file_name_formatters import format_file_name


# --------------------------------------------------------------------------------------------------
# Factories
# --------------------------------------------------------------------------------------------------

def make_anilist(*, romaji="Romaji Title", english="English Title", native="ネイティブ題",
                 season=None, year=2021):
    return SimpleNamespace(romaji_title=romaji, english_title=english, native_title=native,
                           season=season, season_year=year)


def make_tvdb_show(*, english_title="TVDB Title", year=2021):
    return SimpleNamespace(english_title=english_title, year=year)


def make_tracked_anime(*, show_folder_name, processing_settings, tvdb_structure_enabled):
    # tvdb_structure_enabled lives on TrackedAnime; format_file_name reads it via
    # processing_settings.tracked_anime, which back-populates to this instance.
    return TrackedAnime(
        show_folder_name=show_folder_name, processing_settings=processing_settings,
        tvdb_structure_enabled=tvdb_structure_enabled,
    )


def make_settings(*, raw_format="{episode_number}",
                  episode_format="{episode_number}",
                  titleless_format="{episode_number}",
                  episode_number_padding=2,
                  season_number_padding=2):
    return TrackedAnimeProcessingSettings(
        raw_episode_file_name_format=raw_format,
        episode_file_name_format=episode_format,
        titleless_episode_file_name_format=titleless_format,
        episode_number_padding=episode_number_padding,
        season_number_padding=season_number_padding,
    )


def make_torrent(*, episode, episode_part=0, episode_part_ceiling=0,
                 encoding=Encoding.HEVC, resolution=Resolution.P1080, release_group="SubsPlease"):
    return Torrent(
        tracked_anime_episode=episode,
        episode_part=episode_part,
        episode_part_ceiling=episode_part_ceiling,
        encoding=encoding,
        resolution=resolution,
        release_group=release_group,
    )


def make_episode(*, episode_number=1, tvdb_episode_ids=(),
                 tvdb_episode_part=None, tvdb_episode_part_ceiling=None):
    return TrackedAnimeEpisode(
        episode_number=episode_number,
        tvdb_episode_ids=list(tvdb_episode_ids),
        tvdb_episode_part=tvdb_episode_part,
        tvdb_episode_part_ceiling=tvdb_episode_part_ceiling,
    )


def make_tvdb_episode(*, episode_id, number=None, absolute_number=None, season_number=1, title=None):
    number = episode_id if number is None else number
    absolute_number = number if absolute_number is None else absolute_number
    return TVDBSeriesEpisode(
        id=episode_id, series_id=1, title=title, air_date=None, runtime=None, overview=None,
        image_url=None, number=number, absolute_number=absolute_number, season_number=season_number,
        season_name=None, finale_type=None, season_type=TVDBSeasonType.OFFICIAL,
    )


# Convenience builders for the two common torrent shapes.

def raw_torrent(episode_number, *, part=0, part_ceiling=0):
    return make_torrent(episode=make_episode(episode_number=episode_number),
                        episode_part=part, episode_part_ceiling=part_ceiling)


def tvdb_torrent(tvdb_episode_ids, *, episode_number=1, part=0, part_ceiling=0,
                 tvdb_episode_part=None, tvdb_episode_part_ceiling=None):
    episode = make_episode(episode_number=episode_number, tvdb_episode_ids=tvdb_episode_ids,
                           tvdb_episode_part=tvdb_episode_part,
                           tvdb_episode_part_ceiling=tvdb_episode_part_ceiling)
    return make_torrent(episode=episode, episode_part=part, episode_part_ceiling=part_ceiling)


# --------------------------------------------------------------------------------------------------
# Call helpers — assemble the full call so cases stay focused on what varies.
# --------------------------------------------------------------------------------------------------

def call_raw(db_torrents, *, fmt="{episode_number}", padding=2, anilist=None, tvdb_show=None):
    settings = make_settings(raw_format=fmt, episode_number_padding=padding)
    tracked_anime = make_tracked_anime(show_folder_name="", processing_settings=settings,
                                       tvdb_structure_enabled=False)
    return format_file_name(tracked_anime, anilist or make_anilist(), tvdb_show or make_tvdb_show(),
                            [], db_torrents)


def call_tvdb(db_torrents, tvdb_episodes, *, fmt="{episode_number}", titleless_fmt=None,
              episode_padding=2, season_padding=2, anilist=None, tvdb_show=None):
    # Both formats default to the same string, so cases that don't care about title-based format
    # selection get a stable output regardless of whether a title happens to be present.
    settings = make_settings(episode_format=fmt, titleless_format=titleless_fmt or fmt,
                             episode_number_padding=episode_padding, season_number_padding=season_padding)
    tracked_anime = make_tracked_anime(show_folder_name="", processing_settings=settings,
                                       tvdb_structure_enabled=True)
    return format_file_name(tracked_anime, anilist or make_anilist(), tvdb_show or make_tvdb_show(),
                            tvdb_episodes, db_torrents)


@dataclass
class Case:
    id: str
    call: Callable[[], str]
    expected_result: str | None = None
    expected_exception: type[Exception] | None = None


def _raw_episodes(episode_numbers, expected):
    return Case(id=f"raw episodes {episode_numbers} -> {expected}",
                call=lambda: call_raw([raw_torrent(n) for n in episode_numbers]),
                expected_result=expected)


def _raw_part_reconcile(tvdb_numbers, rp, rc, expected):
    def call():
        ids = list(range(10, 10 + len(tvdb_numbers)))
        episodes = [make_tvdb_episode(episode_id=i, number=n) for i, n in zip(ids, tvdb_numbers)]
        torrent = tvdb_torrent(ids, part=rp, part_ceiling=rc)
        return call_tvdb([torrent], episodes)
    return Case(id=f"raw part reconcile {tvdb_numbers} rp={rp} rc={rc} -> {expected}",
                call=call, expected_result=expected)


def _multi_torrent_part_group(parts, ceiling, expected_suffix):
    def call():
        episodes = [make_tvdb_episode(episode_id=10, number=5)]
        torrents = [tvdb_torrent([10], tvdb_episode_part=p, tvdb_episode_part_ceiling=ceiling) for p in parts]
        return call_tvdb(torrents, episodes)
    return Case(id=f"multi-torrent parts {parts} ceiling={ceiling}",
                call=call, expected_result="05" + expected_suffix)


_TWO_TVDB = [make_tvdb_episode(episode_id=10, number=5), make_tvdb_episode(episode_id=11, number=6)]


CASES = [
    # --- Raw branch: episode number rendering ---
    _raw_episodes([5], "05"),                       # single episode
    _raw_episodes([5, 6], "05-06"),                 # contiguous -> range
    _raw_episodes([5, 6, 7], "05-07"),              # contiguous range collapses to first-last
    _raw_episodes([5, 7], "05 & 07"),               # gap -> ampersand join
    _raw_episodes([5, 7, 9], "05 & 07 & 09"),       # multiple gaps
    _raw_episodes([7, 5, 6], "05-07"),              # input order doesn't matter
    Case(id="raw padding is respected",
         call=lambda: call_raw([raw_torrent(5)], padding=3), expected_result="005"),
    Case(id="raw part is appended",
         call=lambda: call_raw([raw_torrent(5, part=1, part_ceiling=2)]), expected_result="05 Part 1"),
    # tvdb ids present on the episode, but with structure disabled the raw number wins
    Case(id="raw branch ignores tvdb mapping",
         call=lambda: call_raw([tvdb_torrent([99], episode_number=5)]), expected_result="05"),

    # --- Raw branch: metadata tokens ---
    Case(id="all shared tokens substituted",
         call=lambda: call_raw(
             [raw_torrent(5)],
             fmt="{anilist_title_english} ({season_year}) [{release_group}][{resolution}][{encoding}] - {episode_number}",
             anilist=make_anilist(english="Frieren", year=2023)),
         expected_result="Frieren (2023) [SubsPlease][1080p][HEVC] - 05"),
    Case(id="english title falls back to romaji",
         call=lambda: call_raw([raw_torrent(5)], fmt="{anilist_title_english}",
                               anilist=make_anilist(english="", romaji="Sousou no Frieren")),
         expected_result="Sousou no Frieren"),
    Case(id="romaji falls back to native",
         call=lambda: call_raw([raw_torrent(5)], fmt="{anilist_title_romaji}|{anilist_title_english}",
                               anilist=make_anilist(english="", romaji="", native="葬送のフリーレン")),
         expected_result="葬送のフリーレン⏐葬送のフリーレン"),
    Case(id="season title cased",
         call=lambda: call_raw([raw_torrent(5)], fmt="{season}",
                               anilist=make_anilist(season=AnilistAnimeSeason.FALL)),
         expected_result="Fall"),
    Case(id="season unknown when missing",
         call=lambda: call_raw([raw_torrent(5)], fmt="{season}", anilist=make_anilist(season=None)),
         expected_result="Unknown"),
    Case(id="year falls back to tvdb show",
         call=lambda: call_raw([raw_torrent(5)], fmt="{season_year}",
                               anilist=make_anilist(year=None), tvdb_show=make_tvdb_show(year=2019)),
         expected_result="2019"),
    Case(id="year unknown when missing everywhere",
         call=lambda: call_raw([raw_torrent(5)], fmt="{season_year}",
                               anilist=make_anilist(year=None), tvdb_show=make_tvdb_show(year=None)),
         expected_result="Unknown"),

    # --- TVDB branch: single episode & tokens ---
    Case(id="tvdb episode number",
         call=lambda: call_tvdb([tvdb_torrent([10])], [make_tvdb_episode(episode_id=10, number=5)]),
         expected_result="05"),
    Case(id="tvdb absolute number token",
         call=lambda: call_tvdb([tvdb_torrent([10])],
                                [make_tvdb_episode(episode_id=10, number=5, absolute_number=29)],
                                fmt="{absolute_episode_number}"),
         expected_result="29"),
    Case(id="tvdb season number token is padded",
         call=lambda: call_tvdb([tvdb_torrent([10])],
                                [make_tvdb_episode(episode_id=10, number=5, season_number=2)],
                                fmt="{season_number}", season_padding=2),
         expected_result="02"),
    Case(id="tvdb episode title token",
         call=lambda: call_tvdb([tvdb_torrent([10])],
                                [make_tvdb_episode(episode_id=10, number=5, title="The Journey's End")],
                                fmt="{episode_number} - {episode_title}"),
         expected_result="05 - The Journey's End"),

    # --- TVDB branch: format selection ---
    Case(id="titleless format used when no title",
         call=lambda: call_tvdb([tvdb_torrent([10])],
                                [make_tvdb_episode(episode_id=10, number=5, title=None)],
                                fmt="TITLED {episode_number}", titleless_fmt="RAW {episode_number}"),
         expected_result="RAW 05"),
    Case(id="titled format used when any title present",
         call=lambda: call_tvdb([tvdb_torrent([10])],
                                [make_tvdb_episode(episode_id=10, number=5, title="Ep Title")],
                                fmt="TITLED {episode_number}", titleless_fmt="RAW {episode_number}"),
         expected_result="TITLED 05"),

    # --- TVDB branch: multiple episodes ---
    Case(id="one torrent mapping to several episodes",
         call=lambda: call_tvdb([tvdb_torrent([10, 11])], _TWO_TVDB), expected_result="05-06"),
    Case(id="several torrents are unioned",
         call=lambda: call_tvdb([tvdb_torrent([10]), tvdb_torrent([11])], _TWO_TVDB),
         expected_result="05-06"),
    Case(id="non-contiguous episodes join with ampersand",
         call=lambda: call_tvdb([tvdb_torrent([10, 11])],
                                [make_tvdb_episode(episode_id=10, number=5),
                                 make_tvdb_episode(episode_id=11, number=8)]),
         expected_result="05 & 08"),
    Case(id="absolute numbers render as their own range",
         call=lambda: call_tvdb([tvdb_torrent([10, 11])],
                                [make_tvdb_episode(episode_id=10, number=5, absolute_number=29),
                                 make_tvdb_episode(episode_id=11, number=6, absolute_number=30)],
                                fmt="{absolute_episode_number}"),
         expected_result="29-30"),

    # --- TVDB branch: single-torrent parts ---
    Case(id="tvdb part rendered when present",
         call=lambda: call_tvdb([tvdb_torrent([10], tvdb_episode_part=2, tvdb_episode_part_ceiling=3)],
                                [make_tvdb_episode(episode_id=10, number=5)]),
         expected_result="05 Part 2"),
    Case(id="raw part used when no tvdb part",
         call=lambda: call_tvdb([tvdb_torrent([10], part=1, part_ceiling=2)],
                                [make_tvdb_episode(episode_id=10, number=5)]),
         expected_result="05 Part 1"),
    Case(id="tvdb part takes precedence over raw part",
         call=lambda: call_tvdb([tvdb_torrent([10], part=1, part_ceiling=2,
                                              tvdb_episode_part=2, tvdb_episode_part_ceiling=3)],
                                [make_tvdb_episode(episode_id=10, number=5)]),
         expected_result="05 Part 2"),
    # rc == k -> the raw part picks the rp-th episode whole (no part suffix)
    _raw_part_reconcile([5, 6, 7], 1, 3, "05"),
    _raw_part_reconcile([5, 6, 7], 2, 3, "06"),
    _raw_part_reconcile([5, 6, 7], 3, 3, "07"),
    # k % rc == 0 -> each part is a contiguous block of whole episodes
    _raw_part_reconcile([5, 6, 7, 8], 1, 2, "05-06"),
    _raw_part_reconcile([5, 6, 7, 8], 2, 2, "07-08"),
    # rc % k == 0 (rc > k) -> the part addresses a sub-part of a single episode
    _raw_part_reconcile([5, 6], 1, 4, "05 Part 1"),
    _raw_part_reconcile([5, 6], 2, 4, "05 Part 2"),
    _raw_part_reconcile([5, 6], 3, 4, "06 Part 1"),
    _raw_part_reconcile([5, 6], 4, 4, "06 Part 2"),
    Case(id="unreconcilable part count raises",
         call=lambda: call_tvdb([tvdb_torrent([10, 11], part=1, part_ceiling=3)], _TWO_TVDB),
         expected_exception=TorrentEpisodeCountMismatch),

    # --- TVDB branch: multi-torrent parts ---
    _multi_torrent_part_group([1, 2], 3, " Part 1-2"),     # contiguous group, incomplete -> range
    _multi_torrent_part_group([1, 2, 3], 4, " Part 1-3"),  # contiguous group collapses to first-last
    _multi_torrent_part_group([1, 3], 4, " Part 1&3"),     # gap -> ampersand join
    Case(id="complete part set drops the suffix",
         call=lambda: call_tvdb(
             [tvdb_torrent([10], tvdb_episode_part=1, tvdb_episode_part_ceiling=2),
              tvdb_torrent([10], tvdb_episode_part=2, tvdb_episode_part_ceiling=2)],
             [make_tvdb_episode(episode_id=10, number=5)]),
         expected_result="05"),
    Case(id="parts across different episodes are dropped",
         call=lambda: call_tvdb(
             [tvdb_torrent([10], tvdb_episode_part=1, tvdb_episode_part_ceiling=2),
              tvdb_torrent([11], tvdb_episode_part=1, tvdb_episode_part_ceiling=2)],
             _TWO_TVDB),
         expected_result="05-06"),

    # --- Episode-number prefix detection (E/Ep/... immediately before the token) ---
    Case(id="letter prefix repeated inside a range",
         call=lambda: call_tvdb([tvdb_torrent([10, 11])], _TWO_TVDB,
                                fmt="S{season_number}E{episode_number}"),
         expected_result="S01E05-E06"),
    Case(id="letter prefix joins non-contiguous numbers",
         call=lambda: call_tvdb([tvdb_torrent([10, 11])],
                                [make_tvdb_episode(episode_id=10, number=5),
                                 make_tvdb_episode(episode_id=11, number=7)],
                                fmt="S{season_number}E{episode_number}"),
         expected_result="S01E05E07"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_format_file_name(case: Case):
    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            case.call()
        return
    assert case.call() == case.expected_result
