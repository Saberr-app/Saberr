from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest


def _db_torrent(*, torrent_id, episode_id, download_id, anilist_id, episode_number, episode_part,
                episode_part_ceiling):
    tracked_anime = SimpleNamespace(anilist_id=anilist_id, english_title="English", romaji_title="Romaji",
                                    native_title="Native")
    episode = SimpleNamespace(id=episode_id, episode_number=episode_number, tracked_anime=tracked_anime)
    return SimpleNamespace(id=torrent_id, effective_download=SimpleNamespace(id=download_id),
                           tracked_anime_episode=episode, episode_part=episode_part,
                           episode_part_ceiling=episode_part_ceiling)


def _other_db_torrent(*, torrent_id, episode_id):
    return SimpleNamespace(id=torrent_id, tracked_anime_episode=SimpleNamespace(id=episode_id))


@dataclass
class Case:
    id: str
    # (torrent_id, episode_id) pairs for the sibling-episode torrents
    other_torrents: list[tuple[int, int]] = field(default_factory=list)
    episode_part: int = 0
    episode_part_ceiling: int = 0


CASES = [
    Case(id="single torrent copies download/episode data onto the raw torrent"),
    Case(id="other episode torrents are recorded", other_torrents=[(20, 120), (21, 121)]),
    Case(id="episode part and ceiling are carried over", episode_part=2, episode_part_ceiling=3),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test__populate_processed_raw_torrent(case: Case, make_component, make_raw_torrent):
    raw_torrent = make_raw_torrent()
    db_torrent = _db_torrent(torrent_id=10, episode_id=70, download_id=99, anilist_id=4242, episode_number=7,
                             episode_part=case.episode_part, episode_part_ceiling=case.episode_part_ceiling)
    other_db_torrents = [_other_db_torrent(torrent_id=tid, episode_id=eid) for tid, eid in case.other_torrents]

    component = make_component()

    await component._populate_processed_raw_torrent(raw_torrent=raw_torrent, db_torrent=db_torrent,
                                                    other_db_torrents=other_db_torrents)

    assert raw_torrent.db_torrent_id == 10
    assert raw_torrent.db_episode_id == 70
    assert raw_torrent.db_download_id == 99
    assert raw_torrent.other_episodes_db_torrent_ids == [tid for tid, _ in case.other_torrents]
    assert raw_torrent.other_db_episode_ids == [eid for _, eid in case.other_torrents]
    assert raw_torrent.anilist_episode_number == 7
    assert raw_torrent.episode_part == case.episode_part
    assert raw_torrent.episode_part_ceiling == case.episode_part_ceiling
    # the minimal record is built from the tracked anime's identity, no Anilist fetch
    assert raw_torrent.anilist_anime_min.id == 4242
