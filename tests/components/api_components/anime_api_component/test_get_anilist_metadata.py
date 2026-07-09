from dataclasses import dataclass

import pytest

from tests.support.mocks import patch_async_returns

_COLLECTIONS = "services.anilist_service.AnilistService.get_genre_and_tag_collections"


@dataclass
class Case:
    id: str
    collections: tuple
    expected_genres: list
    expected_tags: list


CASES = [
    Case(id="maps genres and tags",
         collections=(["Action", "Comedy"],
                      [{"name": "Time Skip", "category": "Setting"}, {"name": "Magic", "category": "Theme"}]),
         expected_genres=["Action", "Comedy"],
         expected_tags=[("Time Skip", "Setting"), ("Magic", "Theme")]),
    Case(id="empty collections yield empty lists",
         collections=([], []), expected_genres=[], expected_tags=[]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_anilist_metadata(case: Case, make_component, mocker):
    patch_async_returns(mocker, {_COLLECTIONS: case.collections})

    result = await make_component().get_anilist_metadata()

    assert result.genres == case.expected_genres
    assert [(tag.name, tag.category) for tag in result.tags] == case.expected_tags
