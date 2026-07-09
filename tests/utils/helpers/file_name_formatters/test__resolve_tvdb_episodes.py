from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from common.exceptions import TorrentEpisodeCountMismatch
from utils.helpers.file_name_formatters import _resolve_tvdb_episodes

# a small fixed TVDB episode catalogue, keyed by id
_CATALOGUE = {10: SimpleNamespace(id=10, number=2),
              11: SimpleNamespace(id=11, number=1),
              12: SimpleNamespace(id=12, number=3)}


def _torrent(part=0, ceiling=0):
    return SimpleNamespace(episode_part=part, episode_part_ceiling=ceiling)


def _episode(ids, part=None, ceiling=None):
    return SimpleNamespace(tvdb_episode_ids=ids, tvdb_episode_part=part, tvdb_episode_part_ceiling=ceiling)


@dataclass
class Case:
    id: str
    torrents: list
    episodes: list
    expected_ids: list[int] | None = None
    expected_parts: list[int] | None = None
    expected_raises: bool = False


CASES = [
    Case(id="single torrent maps to its tvdb episodes sorted by number",
         torrents=[_torrent()], episodes=[_episode([11, 10])], expected_ids=[11, 10], expected_parts=None),
    Case(id="single episode with a tvdb part exposes the part",
         torrents=[_torrent()], episodes=[_episode([11], part=2)], expected_ids=[11], expected_parts=[2]),
    Case(id="raw part over a single tvdb episode keeps the raw part",
         torrents=[_torrent(part=1, ceiling=1)], episodes=[_episode([11])],
         expected_ids=[11], expected_parts=[1]),
    Case(id="raw part with an explicit tvdb part prefers the tvdb part",
         torrents=[_torrent(part=2, ceiling=2)], episodes=[_episode([11], part=3)],
         expected_ids=[11], expected_parts=[3]),
    Case(id="raw part ceiling matching the tvdb count selects the nth episode",
         torrents=[_torrent(part=2, ceiling=2)], episodes=[_episode([11, 10])],
         expected_ids=[10], expected_parts=None),
    Case(id="multiple torrents without parts union their episodes",
         torrents=[_torrent(), _torrent()], episodes=[_episode([11]), _episode([10])],
         expected_ids=[11, 10], expected_parts=None),
    Case(id="irreconcilable raw part count raises",
         torrents=[_torrent(part=1, ceiling=3)], episodes=[_episode([11, 10])], expected_raises=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__resolve_tvdb_episodes(case: Case):
    if case.expected_raises:
        with pytest.raises(TorrentEpisodeCountMismatch):
            _resolve_tvdb_episodes(case.torrents, case.episodes, _CATALOGUE)
        return

    episodes, parts = _resolve_tvdb_episodes(case.torrents, case.episodes, _CATALOGUE)

    assert [e.id for e in episodes] == case.expected_ids
    assert parts == case.expected_parts
