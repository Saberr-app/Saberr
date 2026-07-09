from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from constants import AnilistAnimeSeason
from utils.helpers.file_name_formatters import format_show_directory_name


def make_anilist(*, romaji="Romaji Title", english="English Title", native="ネイティブ題",
                 season=AnilistAnimeSeason.FALL, year=2021):
    return SimpleNamespace(romaji_title=romaji, english_title=english, native_title=native,
                           season=season, season_year=year)


def make_tvdb_show(*, english_title="TVDB Title", year=2020):
    return SimpleNamespace(english_title=english_title, year=year)


_SENTINEL = object()


@dataclass
class Case:
    id: str
    fmt: str
    anilist: Any
    tvdb_show: Any = _SENTINEL
    expected_result: str = ""


CASES = [
    Case(id="all tokens substituted",
         fmt=("{anilist_title_english} ({season_year}) [{season}] "
              "{anilist_title_romaji} - {anilist_title_japanese} - {tvdb_title_english}"),
         anilist=make_anilist(),
         expected_result="English Title (2021) [Fall] Romaji Title - ネイティブ題 - TVDB Title"),
    Case(id="english title falls back to romaji",
         fmt="{anilist_title_english}", anilist=make_anilist(english="", romaji="Sousou no Frieren"),
         expected_result="Sousou no Frieren"),
    Case(id="tvdb title falls back to anilist english",
         fmt="{tvdb_title_english}", anilist=make_anilist(english="Frieren"),
         tvdb_show=make_tvdb_show(english_title=""), expected_result="Frieren"),
    Case(id="tvdb title falls back when show is None",
         fmt="{tvdb_title_english}", anilist=make_anilist(english="Frieren"),
         tvdb_show=None, expected_result="Frieren"),
    Case(id="season title cased",
         fmt="{season}", anilist=make_anilist(season=AnilistAnimeSeason.FALL), expected_result="Fall"),
    Case(id="season unknown when missing",
         fmt="{season}", anilist=make_anilist(season=None), expected_result="Unknown"),
    Case(id="year falls back to tvdb",
         fmt="{season_year}", anilist=make_anilist(year=None), tvdb_show=make_tvdb_show(year=2019),
         expected_result="2019"),
    Case(id="year unknown when missing everywhere",
         fmt="{season_year}", anilist=make_anilist(year=None), tvdb_show=make_tvdb_show(year=None),
         expected_result="Unknown"),
    # illegal path characters from the resolved title are sanitised
    Case(id="result is path cleaned",
         fmt="{anilist_title_english}", anilist=make_anilist(english="A:B"), expected_result="A꞉B"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_format_show_directory_name(case: Case):
    tvdb_show = make_tvdb_show() if case.tvdb_show is _SENTINEL else case.tvdb_show
    assert format_show_directory_name(case.fmt, case.anilist, tvdb_show) == case.expected_result
