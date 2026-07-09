from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from common.exceptions import ObjectNotFoundException
from components.operational_components.tracked_anime_component import TrackedAnimeComponent

_REPO = "repositories.tracked_anime_repositories.tracked_anime_repo.TrackedAnimeRepo"


def _ta(id_, anilist_id):
    return SimpleNamespace(id=id_, anilist_id=anilist_id)


@dataclass
class Case:
    id: str
    tracked_anime_ids: list[int] | None = None
    anilist_ids: list[int] | None = None
    found: list = field(default_factory=list)
    expected_ids: list[int] | None = None
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="neither selector raises value error", expected_exception=ValueError),
    Case(id="resolves by tracked anime ids", tracked_anime_ids=[1, 2],
         found=[_ta(1, 10), _ta(2, 20)], expected_ids=[1, 2]),
    Case(id="missing tracked anime id raises not found", tracked_anime_ids=[1, 2],
         found=[_ta(1, 10)], expected_exception=ObjectNotFoundException),
    Case(id="resolves by anilist ids", anilist_ids=[10, 20],
         found=[_ta(1, 10), _ta(2, 20)], expected_ids=[1, 2]),
    Case(id="missing anilist id raises not found", anilist_ids=[10, 99],
         found=[_ta(1, 10)], expected_exception=ObjectNotFoundException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test__resolve_tracked_anime(case: Case, mocker):
    repo = mocker.patch(f"{_REPO}.get_tracked_anime_list", return_value=case.found)
    component = TrackedAnimeComponent()

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await component._resolve_tracked_anime(case.tracked_anime_ids, case.anilist_ids)
        return

    result = await component._resolve_tracked_anime(case.tracked_anime_ids, case.anilist_ids)
    assert [ta.id for ta in result] == case.expected_ids
    # anilist_ids are only forwarded when no tracked ids were given
    assert repo.await_args.kwargs["anilist_ids"] == (case.anilist_ids if not case.tracked_anime_ids else None)
