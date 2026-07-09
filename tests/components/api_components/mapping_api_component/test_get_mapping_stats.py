from dataclasses import dataclass
from datetime import datetime
from unittest.mock import AsyncMock, PropertyMock

import pytest

from components.api_components.mapping_api_component import MappingAPIComponent

_RELATIONS_COUNT = "utils.anime_relations.AnimeRelations.anime_relations_offset_map_count"
_MAPPINGS_COUNT = "utils.anime_relations.AnimeRelations.anilist_tvdb_mappings_count"
_MAPPINGS_UPDATED = "utils.anime_relations.AnimeRelations.anilist_tvdb_mappings_last_updated"
_RELATIONS_UPDATED = "utils.anime_relations.AnimeRelations.anime_relations_offset_map_last_updated"


@dataclass
class Case:
    id: str
    relations_count: int
    mappings_count: int
    relations_updated_at: datetime
    mappings_updated_at: datetime


CASES = [
    Case(id="stats are read straight from anime_relations", relations_count=10, mappings_count=20,
         relations_updated_at=datetime(2024, 3, 4), mappings_updated_at=datetime(2024, 1, 2)),
    Case(id="zero counts", relations_count=0, mappings_count=0,
         relations_updated_at=datetime(2020, 1, 1), mappings_updated_at=datetime(2020, 1, 1)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_mapping_stats(case: Case, mocker):
    mocker.patch(_RELATIONS_COUNT, new_callable=PropertyMock, return_value=case.relations_count)
    mocker.patch(_MAPPINGS_COUNT, new_callable=PropertyMock, return_value=case.mappings_count)
    mocker.patch(_MAPPINGS_UPDATED, new_callable=AsyncMock, return_value=case.mappings_updated_at)
    mocker.patch(_RELATIONS_UPDATED, new_callable=AsyncMock, return_value=case.relations_updated_at)

    response = await MappingAPIComponent.__new__(MappingAPIComponent).get_mapping_stats()

    assert response.anime_relations_count == case.relations_count
    assert response.anilist_tvdb_mappings_count == case.mappings_count
    assert response.anime_relations_last_updated_at == case.relations_updated_at
    assert response.anilist_tvdb_mappings_last_updated_at == case.mappings_updated_at
