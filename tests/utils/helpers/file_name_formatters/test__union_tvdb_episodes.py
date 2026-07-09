from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from utils.helpers.file_name_formatters import _union_tvdb_episodes


def _tvdb(id_, number):
    return SimpleNamespace(id=id_, number=number)


@dataclass
class Case:
    id: str
    by_id: dict
    episodes: list
    expected_ids: list[int]


CASES = [
    Case(id="dedupes by id and sorts by number",
         by_id={10: _tvdb(10, 2), 11: _tvdb(11, 1)},
         episodes=[SimpleNamespace(tvdb_episode_ids=[10, 11]), SimpleNamespace(tvdb_episode_ids=[11])],
         # the shared id 11 appears once; ordering is by episode number (1 then 2)
         expected_ids=[11, 10]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__union_tvdb_episodes(case: Case):
    def tvdb_episodes_for(episode):
        return sorted((case.by_id[i] for i in episode.tvdb_episode_ids), key=lambda e: e.number)

    result = _union_tvdb_episodes(case.episodes, tvdb_episodes_for)

    assert [e.id for e in result] == case.expected_ids
