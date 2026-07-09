from dataclasses import dataclass

import pytest

from common.exceptions import ExternalServiceException
from components.api_components.user_anime_list_api_component import UserAnimeListAPIComponent
from dto.anilist import AnilistAnime
from tests.support.builders import make_anime, make_entry

_ANILIST = "components.service_components.anilist_component.AnilistComponent"


@dataclass
class Case:
    id: str
    anime_records: list[AnilistAnime]
    expected_keys: set[int] | None = None
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="maps records by anilist id",
         anime_records=[make_anime(1), make_anime(2)], expected_keys={1, 2}),
    Case(id="raises when a record is missing",
         anime_records=[make_anime(1)], expected_exception=ExternalServiceException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test__hydrate_anime(case: Case, mocker):
    entries = [make_entry(1), make_entry(2)]
    mocker.patch(f"{_ANILIST}.get_anime_records", return_value=case.anime_records)
    component = UserAnimeListAPIComponent()

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await component._hydrate_anime(entries)
        return

    result = await component._hydrate_anime(entries)

    assert set(result.keys()) == case.expected_keys
