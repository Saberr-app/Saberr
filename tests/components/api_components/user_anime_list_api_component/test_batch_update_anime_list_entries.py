from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from constants import AnilistAnimeUserStatus
from api.schemas.user_anime_list_schemas import (UserAnimeBatchUpdateRequest,
                                                 UserAnimeBatchUpdateRequestData)


@dataclass
class Case:
    id: str
    anilist_ids: list
    entry_specs: list  # dicts passed to make_entry
    tracked: list       # (anilist_id, tracked_anime_id) rows returned by the tracked-anime component
    expected: list      # (anilist_id, expected_tracked_anime_id)
    score: float = 7.0
    status: AnilistAnimeUserStatus = AnilistAnimeUserStatus.CURRENT


CASES = [
    # each returned entry becomes a minimal item; tracked-anime ids are attached by anilist id
    Case(id="maps entries and attaches tracked anime ids",
         anilist_ids=[1, 2],
         entry_specs=[dict(anime_id=1, status="CURRENT", score=8.0, progress=5),
                      dict(anime_id=2, status="COMPLETED", score=6.0, progress=12)],
         tracked=[(1, 99)],
         expected=[(1, 99), (2, None)]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_batch_update_anime_list_entries(case: Case, make_component, make_entry):
    entries = [make_entry(**spec) for spec in case.entry_specs]
    component = make_component([], [])
    component._anilist_list_component.update_user_list_entries = AsyncMock(return_value=entries)
    component._tracked_anime_component.get_tracked_anime_by_anilist_ids = AsyncMock(
        return_value=[SimpleNamespace(anilist_id=aid, id=tid) for aid, tid in case.tracked])

    body = UserAnimeBatchUpdateRequest(
        anilist_ids=case.anilist_ids,
        data=UserAnimeBatchUpdateRequestData(status=case.status, score=case.score))

    result = await component.batch_update_anime_list_entries(body)

    component._anilist_list_component.update_user_list_entries.assert_awaited_once_with(
        anilist_ids=case.anilist_ids, status=case.status, score=case.score)

    entries_by_id = {entry.anime_id: entry for entry in entries}
    assert [(item.anilist_id, item.tracked_anime_id) for item in result.updated_anime_list] == case.expected
    for item in result.updated_anime_list:
        source_entry = entries_by_id[item.anilist_id]
        assert item.anime is None  # the minimal item carries no full anime payload
        assert item.progress == source_entry.progress
        assert item.score == source_entry.score
        assert item.status == source_entry.status
