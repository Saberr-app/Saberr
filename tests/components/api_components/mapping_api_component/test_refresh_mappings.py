from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from components.api_components.mapping_api_component import MappingAPIComponent

_REFRESH = "utils.anime_relations.AnimeRelations.refresh_relations"


@dataclass
class Case:
    id: str


CASES = [
    Case(id="delegates to anime_relations.refresh_relations with raise_on_failure=True"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_refresh_mappings(case: Case, mocker):
    refresh = mocker.patch(_REFRESH, new_callable=AsyncMock)

    result = await MappingAPIComponent.__new__(MappingAPIComponent).refresh_mappings()

    assert result is None
    refresh.assert_awaited_once_with(raise_on_failure=True)
