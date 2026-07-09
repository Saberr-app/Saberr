from dataclasses import dataclass, field

import pytest


@dataclass
class Case:
    id: str
    anilist_id: int
    expected_result: None = None
    expected_delete_calls: list[int] = field(default_factory=list)
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="delegates to list component", anilist_id=42, expected_delete_calls=[42]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_delete_anime_list_item(case: Case, make_component):
    component = make_component([], [])

    result = await component.delete_anime_list_item(anilist_id=case.anilist_id)

    assert result is case.expected_result
    assert component._anilist_list_component.delete_calls == case.expected_delete_calls
