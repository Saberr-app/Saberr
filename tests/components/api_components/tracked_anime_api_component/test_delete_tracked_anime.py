from dataclasses import dataclass

import pytest

from common.exceptions import NotFoundException, ObjectNotFoundException
from components.api_components.tracked_anime_api_component import TrackedAnimeAPIComponent

_TA = "components.operational_components.tracked_anime_component.TrackedAnimeComponent"


@dataclass
class Case:
    id: str
    side_effect: Exception | None = None
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="wraps the single id and forwards to operational delete"),
    # the operational layer raises ObjectNotFoundException; @api_component maps it to NotFoundException
    Case(id="missing object maps to NotFoundException",
         side_effect=ObjectNotFoundException("nope"), expected_exception=NotFoundException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_delete_tracked_anime(case: Case, mocker):
    delete = mocker.patch(f"{_TA}.delete_tracked_anime", side_effect=case.side_effect)

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await TrackedAnimeAPIComponent().delete_tracked_anime(tracked_anime_id=999999)
        return

    await TrackedAnimeAPIComponent().delete_tracked_anime(tracked_anime_id=42)

    delete.assert_awaited_once_with(tracked_anime_ids=[42])
