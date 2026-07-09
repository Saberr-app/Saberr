from dataclasses import dataclass

import pytest

from components.api_components.user_anime_list_api_component import UserAnimeListAPIComponent
from config import config
from constants import AnilistTitleLanguage
from dto.anilist import AnilistAnime


def _anime(english, romaji, native):
    return AnilistAnime.from_dict({"id": 1, "title": {"english": english, "romaji": romaji, "native": native}})


@dataclass
class Case:
    id: str
    language: AnilistTitleLanguage
    english: str | None
    expected_result: str


_ROMAJI = "Romaji Title"
_NATIVE = "Native Title"


CASES = [
    Case(id="romaji preference", language=AnilistTitleLanguage.ROMAJI, english="English Title",
         expected_result=_ROMAJI),
    Case(id="english preference", language=AnilistTitleLanguage.ENGLISH, english="English Title",
         expected_result="English Title"),
    Case(id="english preference falls back to romaji when english missing",
         language=AnilistTitleLanguage.ENGLISH, english=None, expected_result=_ROMAJI),
    Case(id="native preference", language=AnilistTitleLanguage.NATIVE, english="English Title",
         expected_result=_NATIVE),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__title_key(case: Case):
    config.user_settings.anilist_preferred_title_language = case.language
    anime = _anime(case.english, _ROMAJI, _NATIVE)
    assert UserAnimeListAPIComponent._title_key(anime) == case.expected_result
