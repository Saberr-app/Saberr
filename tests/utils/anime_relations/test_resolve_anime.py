from dataclasses import dataclass, field

import pytest

from common.exceptions import AnilistRelationsEpisodeCountMismatch


def relation(other_anilist_id, this_range, other_range):
    return {"other_anilist_id": other_anilist_id,
            "this_episode_range": this_range, "other_episode_range": other_range}


def offset_map(entries):
    return {anilist_id: {"relations": list(relations)} for anilist_id, relations in entries.items()}


@dataclass
class Case:
    id: str
    anilist_id: int
    episode_number: int
    offset_map: dict = field(default_factory=dict)
    episode_count: dict = field(default_factory=dict)
    expected_result: tuple[int, int] | None = None
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="identity when id unknown", anilist_id=100, episode_number=5, expected_result=(100, 5)),
    Case(id="identity when no relations",
         offset_map={100: {"relations": []}},
         anilist_id=100, episode_number=5, expected_result=(100, 5)),
    Case(id="single hop redirect",
         offset_map=offset_map({100: [relation(200, (1, 12), (1, 12))]}),
         anilist_id=100, episode_number=3, expected_result=(200, 3)),
    # this 13-24 maps onto other 1-12
    Case(id="redirect applies episode offset",
         offset_map=offset_map({100: [relation(200, (13, 24), (1, 12))]}),
         anilist_id=100, episode_number=14, expected_result=(200, 2)),
    Case(id="episode outside any relation range is identity",
         offset_map=offset_map({100: [relation(200, (1, 12), (1, 12))]}),
         anilist_id=100, episode_number=20, expected_result=(100, 20)),
    Case(id="multi-hop chaining",
         offset_map=offset_map({
             100: [relation(200, (1, 12), (1, 12))],
             200: [relation(300, (1, 12), (1, 12))],
         }),
         anilist_id=100, episode_number=5, expected_result=(300, 5)),
    Case(id="self-referencing relation is identity",
         offset_map=offset_map({100: [relation(100, (1, 12), (1, 12))]}),
         anilist_id=100, episode_number=5, expected_result=(100, 5)),
    Case(id="cycle is broken",
         offset_map=offset_map({
             100: [relation(200, (1, 12), (1, 12))],
             200: [relation(100, (1, 12), (1, 12))],
         }),
         anilist_id=100, episode_number=5, expected_result=(100, 5)),
    # ep is within the known episode count -> returned as-is, redirect not followed
    Case(id="episode count short-circuits before redirect",
         offset_map=offset_map({100: [relation(200, (1, 12), (1, 12))]}),
         episode_count={100: 12},
         anilist_id=100, episode_number=5, expected_result=(100, 5)),
    Case(id="episode count does not short-circuit when episode exceeds count",
         offset_map=offset_map({100: [relation(200, (13, 24), (1, 12))]}),
         episode_count={100: 12},
         anilist_id=100, episode_number=13, expected_result=(200, 1)),
    Case(id="range length mismatch raises",
         offset_map=offset_map({100: [relation(200, (1, 12), (1, 6))]}),
         anilist_id=100, episode_number=3,
         expected_exception=AnilistRelationsEpisodeCountMismatch),
    Case(id="first matching relation is used",
         offset_map=offset_map({100: [
             relation(200, (1, 12), (1, 12)),
             relation(300, (13, 24), (1, 12)),
         ]}),
         anilist_id=100, episode_number=14, expected_result=(300, 2)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_resolve_anime(case: Case, make_relations):
    ar = make_relations(offset_map=case.offset_map, episode_count=case.episode_count)

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await ar.resolve_anime(case.anilist_id, case.episode_number)
        return

    result = await ar.resolve_anime(case.anilist_id, case.episode_number)
    assert result == case.expected_result
