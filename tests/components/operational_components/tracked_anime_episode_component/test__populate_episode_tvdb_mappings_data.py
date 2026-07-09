from dataclasses import dataclass, field
from unittest.mock import AsyncMock

import pytest

from common.exceptions import TVDBIncompleteDataException


@dataclass
class Case:
    id: str
    mappings: list = field(default_factory=lambda: [(100, 1, 3)])  # (series_id, season_number, episode_number)
    tvdb_episodes: list | None = field(default_factory=list)        # (season, number, id); None => fetch raises
    raise_on_unavailability: bool = False
    expected_exception: type[Exception] | None = None
    expected_fetch_called: bool = True
    expected_episode_id: int | None = None   # resulting mapping.episode_id (first mapping)


CASES = [
    Case(id="no mappings skips the tvdb fetch",
         mappings=[], expected_fetch_called=False),
    Case(id="populates episode id from the matching tvdb episode",
         tvdb_episodes=[(1, 2, 500), (1, 3, 501), (2, 3, 999)], expected_episode_id=501),
    Case(id="fetch failure raises when requested",
         tvdb_episodes=None, raise_on_unavailability=True, expected_exception=TVDBIncompleteDataException),
    Case(id="fetch failure is swallowed by default",
         tvdb_episodes=None, expected_episode_id=None),
    Case(id="unresolved mapping raises when requested",
         tvdb_episodes=[(1, 99, 500)], raise_on_unavailability=True,
         expected_exception=TVDBIncompleteDataException),
    Case(id="unresolved mapping is swallowed by default",
         tvdb_episodes=[(1, 99, 500)], expected_episode_id=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_populate_episode_tvdb_mappings_data(case: Case, make_component, make_mapping,
                                                   make_tvdb_episodes):
    mappings = [make_mapping(series_id=s, season_number=sn, episode_number=en)
                for (s, sn, en) in case.mappings]

    component = make_component()
    if case.tvdb_episodes is None:
        component._tvdb_component.get_series_episodes = AsyncMock(side_effect=RuntimeError("tvdb down"))
    else:
        component._tvdb_component.get_series_episodes = AsyncMock(
            return_value=make_tvdb_episodes(case.tvdb_episodes))

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await component._populate_episode_tvdb_mappings_data(
                tvdb_mappings=mappings, raise_on_tvdb_unavailability=case.raise_on_unavailability)
        return

    await component._populate_episode_tvdb_mappings_data(
        tvdb_mappings=mappings, raise_on_tvdb_unavailability=case.raise_on_unavailability)

    assert (component._tvdb_component.get_series_episodes.await_count == 1) == case.expected_fetch_called
    if mappings:
        assert mappings[0].episode_id == case.expected_episode_id
