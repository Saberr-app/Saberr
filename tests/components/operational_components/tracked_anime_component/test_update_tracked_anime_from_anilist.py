from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from components.operational_components.tracked_anime_component import TrackedAnimeComponent
from tests.support.builders import make_anime

_REPO = "repositories.tracked_anime_repositories.tracked_anime_repo.TrackedAnimeRepo"


def _tracked(anilist_id, romaji, native, english):
    return SimpleNamespace(id=anilist_id, anilist_id=anilist_id, romaji_title=romaji,
                           native_title=native, english_title=english)


@dataclass
class Case:
    id: str
    tracked: object
    expected_update: bool


CASES = [
    # make_anime sets all three titles equal to its `title` argument
    Case(id="title change triggers a batch update",
         tracked=_tracked(1, "Old", "Old", "Old"), expected_update=True),
    Case(id="unchanged titles skip the update",
         tracked=_tracked(1, "Same", "Same", "Same"), expected_update=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_tracked_anime_from_anilist(case: Case, mocker):
    record = make_anime(1, title="Same")
    mocker.patch(f"{_REPO}.get_tracked_anime_list", return_value=[case.tracked])
    batch = mocker.patch(f"{_REPO}.batch_update_tracked_anime")

    await TrackedAnimeComponent().update_tracked_anime_from_anilist(anime_records=[record])

    if case.expected_update:
        batch.assert_awaited_once()
        mapping = batch.await_args.kwargs["update_mappings"][0]
        assert mapping == {"id": 1, "romaji_title": "Same", "native_title": "Same", "english_title": "Same"}
    else:
        batch.assert_not_awaited()
