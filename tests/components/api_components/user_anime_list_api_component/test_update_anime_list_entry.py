from dataclasses import dataclass, field

import pytest

from api.schemas.user_anime_list_schemas import UserAnimeUpdateRequest, UserAnimeUpdateResponse
from api.schemas.anime_schemas import AnimeItem


def _update_request() -> UserAnimeUpdateRequest:
    return UserAnimeUpdateRequest(
        progress=7,
        score=8.5,
        status="CURRENT",
        repeat_count=1,
        is_private=True,
        started_at=AnimeItem.AnilistDate(year=2022, month=4, day=1),
        completed_at=AnimeItem.AnilistDate(year=None, month=None, day=None),
        notes="great",
    )


@dataclass
class Case:
    id: str
    anilist_id: int
    body: UserAnimeUpdateRequest = field(default_factory=_update_request)
    # per-case mock seeds
    anime_kwargs: dict = field(default_factory=dict)
    entry_kwargs: dict = field(default_factory=dict)
    schedules: dict | None = None
    # which assertion shape to run
    assert_forwarded_body: bool = False
    assert_mapped_response: bool = False
    expected_next_airing: tuple[int, int] | None = None
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="forwards body to list component",
         anilist_id=1,
         anime_kwargs=dict(title="Beta"),
         entry_kwargs=dict(status="CURRENT", score=8.5, progress=7),
         assert_forwarded_body=True),
    Case(id="returns mapped update response",
         anilist_id=1,
         anime_kwargs=dict(title="Beta", season_year=2021),
         entry_kwargs=dict(status="CURRENT", score=8.5, progress=7, repeat_count=1,
                           is_private=True, notes="great"),
         assert_mapped_response=True),
    Case(id="attaches airing schedule",
         anilist_id=1,
         anime_kwargs=dict(title="Beta"),
         entry_kwargs=dict(status="CURRENT"),
         schedules={1: [(200, 3, 1), (50, 2, 1)]},
         expected_next_airing=(50, 2)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_anime_list_entry(case: Case, make_component, make_entry, make_anime, make_airing):
    anime = make_anime(case.anilist_id, **case.anime_kwargs)
    schedules = None
    if case.schedules is not None:
        schedules = {anilist_id: [make_airing(airing_at=a, episode=e, anilist_id=aid)
                                  for (a, e, aid) in items]
                     for anilist_id, items in case.schedules.items()}
    component = make_component([], [anime], schedules=schedules)
    component._anilist_list_component.update_return = make_entry(case.anilist_id, **case.entry_kwargs)

    result = await component.update_anime_list_entry(anilist_id=case.anilist_id, body=case.body)

    if case.assert_forwarded_body:
        forwarded = component._anilist_list_component.update_calls[0]
        assert forwarded["anilist_anime_id"] == 1
        assert forwarded["progress"] == 7
        assert forwarded["score"] == 8.5
        assert forwarded["repeat_count"] == 1
        assert forwarded["is_private"] is True
        assert forwarded["status"] == case.body.status
        assert forwarded["started_at"] is case.body.started_at
        assert forwarded["completed_at"] is case.body.completed_at
        assert forwarded["notes"] == "great"
        return

    if case.assert_mapped_response:
        assert isinstance(result, UserAnimeUpdateResponse)
        assert result.score == 8.5
        assert result.progress == 7
        assert result.status.value == "CURRENT"
        assert result.is_private is True
        assert result.notes == "great"
        assert result.anime.id == 1
        assert result.anime.english_title == "Beta"
        return

    assert (result.anime.next_airing_episode.airing_at,
            result.anime.next_airing_episode.episode) == case.expected_next_airing
