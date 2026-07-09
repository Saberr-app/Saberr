from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from common.exceptions import NotFoundException
from constants import TrackedAnimeStatus


@dataclass
class Case:
    id: str
    has_entry: bool
    tracked_status: str | None = None  # a TrackedAnimeStatus name, or None when not tracked
    expected_tracked_id: int | None = None
    expected_exception: type[Exception] | None = None


CASES = [
    # an actively-tracked anime attaches its tracked id
    Case(id="entry with active tracked anime attaches tracked id",
         has_entry=True, tracked_status="ACTIVE", expected_tracked_id=99),
    # tracked but archived -> no tracked id attached
    Case(id="archived tracked anime is not attached",
         has_entry=True, tracked_status="ARCHIVED", expected_tracked_id=None),
    Case(id="untracked anime has no tracked id",
         has_entry=True, tracked_status=None, expected_tracked_id=None),
    Case(id="missing list entry raises NotFound",
         has_entry=False, expected_exception=NotFoundException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_anime_list_entry(case: Case, make_component, make_anime, make_entry):
    anime = make_anime(1, "Title")
    entry = make_entry(1, status="CURRENT", score=8.0, progress=5) if case.has_entry else None
    component = make_component([], [anime])
    component._anilist_list_component.get_user_anime_list_entry = AsyncMock(return_value=entry)
    component._anilist_component.get_anime = AsyncMock(return_value=anime)
    tracked = SimpleNamespace(id=99, status=TrackedAnimeStatus[case.tracked_status]) \
        if case.tracked_status else None
    component._tracked_anime_component.get_tracked_anime = AsyncMock(return_value=tracked)

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await component.get_anime_list_entry(anilist_id=1, force_freshness=False)
        return

    result = await component.get_anime_list_entry(anilist_id=1, force_freshness=False)

    assert result.anime.id == 1
    assert result.tracked_anime_id == case.expected_tracked_id
    assert result.progress == entry.progress
    assert result.score == entry.score
