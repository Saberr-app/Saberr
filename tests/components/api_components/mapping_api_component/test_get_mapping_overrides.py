from dataclasses import dataclass, field
from unittest.mock import AsyncMock

import pytest

from components.api_components.mapping_api_component import MappingAPIComponent
from components.service_components.anilist_component import AnilistComponent
from components.service_components.tvdb_component import TVDBComponent
from dto.orm_models import MappingOverride
from tests.support.builders import make_anime, make_mapping_override, make_tvdb_series

_GET_ALL = "repositories.mapping_override_repo.MappingOverrideRepo.get_all_mapping_overrides"
_ANIME_RECORDS = "components.service_components.anilist_component.AnilistComponent.get_anime_records"
_GET_SERIES = "components.service_components.tvdb_component.TVDBComponent.get_series"


def _component() -> MappingAPIComponent:
    component = MappingAPIComponent.__new__(MappingAPIComponent)
    component._anilist_component = AnilistComponent.__new__(AnilistComponent)
    component._tvdb_component = TVDBComponent.__new__(TVDBComponent)
    return component


@dataclass
class Case:
    id: str
    overrides: list[MappingOverride] = field(default_factory=list)
    expected_len: int = 0


CASES = [
    Case(id="single override is mapped", overrides=[make_mapping_override(anilist_id=100)], expected_len=1),
    Case(id="no overrides -> empty list", overrides=[], expected_len=0),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_mapping_overrides(case: Case, mocker):
    anime = make_anime(100)
    series = make_tvdb_series()
    mocker.patch(_GET_ALL, new_callable=AsyncMock, return_value=case.overrides)
    mocker.patch(_ANIME_RECORDS, new_callable=AsyncMock, return_value=[anime] if case.overrides else [])
    mocker.patch(_GET_SERIES, new_callable=AsyncMock, return_value=series)

    response = await _component().get_mapping_overrides()

    assert len(response.mapping_overrides) == case.expected_len
    if case.expected_len:
        item = response.mapping_overrides[0]
        assert item.id == case.overrides[0].id
        assert item.anilist_id == 100
        assert item.anilist_romaji_title == anime.romaji_title
        assert item.tvdb_title == (series.english_title or series.title)
