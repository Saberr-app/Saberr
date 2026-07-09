from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from common.exceptions import AnilistNotFoundException
from constants import MetadataSource

_GET_ANIME = "components.service_components.anilist_component.AnilistComponent.get_anime"
_TVDB_SERIES_ID = "app_state.anime_relations.get_anilist_id_tvdb_series_id"
_TVDB_COMPONENT = "components.api_components.anime_api_component.TVDBComponent"


def anime(*, romaji="Romaji", english="English", native="Native"):
    return SimpleNamespace(romaji_title=romaji, english_title=english, native_title=native)


def alias(title, language):
    return SimpleNamespace(title=title, language=language)


@dataclass
class Case:
    id: str
    anime: object | None
    tvdb_series_id: int | None = None
    tvdb_aliases: list = field(default_factory=list)
    tvdb_raises: bool = False
    expected_titles: list = field(default_factory=list)  # (source, title, language)
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="missing anime raises not found",
         anime=None, expected_exception=AnilistNotFoundException),
    # all three anilist titles present, no tvdb mapping
    Case(id="all anilist titles, no tvdb mapping",
         anime=anime(), tvdb_series_id=None,
         expected_titles=[(MetadataSource.ANILIST, "Romaji", "Romaji"),
                          (MetadataSource.ANILIST, "English", "English"),
                          (MetadataSource.ANILIST, "Native", "Native")]),
    # blank english title is skipped
    Case(id="blank titles are skipped",
         anime=anime(english="", native=""), tvdb_series_id=None,
         expected_titles=[(MetadataSource.ANILIST, "Romaji", "Romaji")]),
    # tvdb aliases are appended after the anilist titles
    Case(id="tvdb aliases are appended when a series is mapped",
         anime=anime(), tvdb_series_id=55,
         tvdb_aliases=[alias("Alias EN", "eng"), alias("Alias JP", "jpn")],
         expected_titles=[(MetadataSource.ANILIST, "Romaji", "Romaji"),
                          (MetadataSource.ANILIST, "English", "English"),
                          (MetadataSource.ANILIST, "Native", "Native"),
                          (MetadataSource.TVDB, "Alias EN", "eng"),
                          (MetadataSource.TVDB, "Alias JP", "jpn")]),
    # a tvdb lookup failure is swallowed; anilist titles still return
    Case(id="tvdb failure is swallowed",
         anime=anime(), tvdb_series_id=55, tvdb_raises=True,
         expected_titles=[(MetadataSource.ANILIST, "Romaji", "Romaji"),
                          (MetadataSource.ANILIST, "English", "English"),
                          (MetadataSource.ANILIST, "Native", "Native")]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_anime_titles(case: Case, make_component, mocker):
    mocker.patch(_GET_ANIME, return_value=case.anime)
    mocker.patch(_TVDB_SERIES_ID, return_value=case.tvdb_series_id)
    tvdb_cls = mocker.patch(_TVDB_COMPONENT)
    if case.tvdb_raises:
        tvdb_cls.return_value.get_series = AsyncMock(side_effect=RuntimeError("tvdb down"))
    else:
        tvdb_cls.return_value.get_series = AsyncMock(return_value=SimpleNamespace(aliases=case.tvdb_aliases))

    component = make_component()
    component.logger = mocker.MagicMock()  # bare __new__ instance has no logger; used on the swallowed-error path

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await component.get_anime_titles(anilist_id=1, force_freshness=False)
        return

    result = await component.get_anime_titles(anilist_id=1, force_freshness=False)

    assert [(t.source, t.title, t.language) for t in result.titles] == case.expected_titles
