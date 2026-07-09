from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from system import UNSET

_COMPONENT = ("components.operational_components.tracked_anime_episode_component"
              ".TrackedAnimeEpisodeComponent")


@dataclass
class Case:
    id: str
    auto_discard: object = UNSET          # UNSET means the argument is omitted
    expected_delegates: bool = True


CASES = [
    Case(id="unset auto_discard is a no-op", auto_discard=UNSET, expected_delegates=False),
    Case(id="explicit auto_discard delegates to get_or_create", auto_discard=False, expected_delegates=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_tracked_anime_episode(case: Case, make_component, mocker):
    get_or_create = mocker.patch(f"{_COMPONENT}.get_or_create_tracked_anime_episode", new=AsyncMock())

    call_kwargs = dict(tracked_anime_id=1, episode_number=2)
    if case.auto_discard is not UNSET:
        call_kwargs["auto_discard"] = case.auto_discard

    await make_component().update_tracked_anime_episode(**call_kwargs)

    if not case.expected_delegates:
        get_or_create.assert_not_awaited()
        return

    get_or_create.assert_awaited_once()
    passed = get_or_create.await_args.kwargs
    assert passed["tracked_anime_id"] == 1
    assert passed["episode_number"] == 2
    assert passed["set_auto_discard_to"] is case.auto_discard
