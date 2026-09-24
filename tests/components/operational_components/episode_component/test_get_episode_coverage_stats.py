from dataclasses import dataclass, field
from datetime import datetime, UTC
from types import SimpleNamespace

import pytest

from components.operational_components.episode_component import EpisodeComponent
from constants import AnilistAnimeStatus as AnimeStatus, TorrentDownloadStatus as Status
from dto.anime_episode import EpisodeCoverageStats as Stats

_PAST_END = SimpleNamespace(parsed_date=lambda: datetime(2020, 1, 1, tzinfo=UTC))
_FUTURE_END = SimpleNamespace(parsed_date=lambda: datetime(2999, 1, 1, tzinfo=UTC))


def ep(number, *download_statuses):
    torrents = [SimpleNamespace(effective_download=SimpleNamespace(status=s) if s else None)
                for s in download_statuses]
    return SimpleNamespace(episode_number=number, torrents=torrents)


def tracked(from_episode, episodes):
    return SimpleNamespace(from_episode=from_episode, episodes=episodes)


def anime(status, *, episodes=12, end_date=None):
    return SimpleNamespace(status=status, episodes=episodes, end_date=end_date)


def schedule(*episode_numbers):
    return [SimpleNamespace(episode=n) for n in episode_numbers]


def stats(latest, total, processed=0, downloading=0, failed=0, covered=frozenset()):
    return Stats(latest_known_episode_number=latest, processed_episode_count=processed,
                 downloading_episode_count=downloading, failed_episode_count=failed,
                 total_episode_count=total, covered_episodes=set(covered))


@dataclass
class Case:
    id: str
    tracked_anime: object
    anime: object
    expected_result: Stats
    airing_schedule: list | None = field(default_factory=list)


CASES = [
    Case(id="finished anime covers every episode",
         tracked_anime=tracked(1, []), anime=anime(AnimeStatus.FINISHED, episodes=12),
         expected_result=stats(latest=12, total=12)),
    Case(id="from_episode shrinks the total",
         tracked_anime=tracked(3, []), anime=anime(AnimeStatus.FINISHED, episodes=12),
         expected_result=stats(latest=12, total=10)),
    Case(id="airing schedule sets latest to next episode minus one",
         tracked_anime=tracked(1, []), anime=anime(AnimeStatus.RELEASING), airing_schedule=schedule(7, 5),
         expected_result=stats(latest=4, total=4)),
    Case(id="missing airing schedule is treated as empty",
         tracked_anime=tracked(1, []), anime=anime(AnimeStatus.RELEASING, end_date=None), airing_schedule=None,
         expected_result=stats(latest=None, total=None)),
    Case(id="from_episode past the latest episode gives a zero total",
         tracked_anime=tracked(10, []), anime=anime(AnimeStatus.RELEASING), airing_schedule=schedule(5),
         expected_result=stats(latest=4, total=0)),
    Case(id="not-yet-released anime has no total",
         tracked_anime=tracked(1, []), anime=anime(AnimeStatus.NOT_YET_RELEASED),
         expected_result=stats(latest=0, total=None)),
    Case(id="releasing with no schedule and no end date is unknown",
         tracked_anime=tracked(1, []), anime=anime(AnimeStatus.RELEASING, end_date=None),
         expected_result=stats(latest=None, total=None)),
    Case(id="releasing but past end date covers every episode",
         tracked_anime=tracked(1, []), anime=anime(AnimeStatus.RELEASING, episodes=12, end_date=_PAST_END),
         expected_result=stats(latest=12, total=12)),
    Case(id="future end date stays unknown",
         tracked_anime=tracked(1, []), anime=anime(AnimeStatus.RELEASING, end_date=_FUTURE_END),
         expected_result=stats(latest=None, total=None)),
    Case(id="counts within window; below-from and above-latest are skipped",
         tracked_anime=tracked(2, [ep(1, Status.PROCESSED), ep(2, Status.PROCESSED),
                                   ep(3, Status.DOWNLOADING), ep(4, Status.FAILED_PROCESSING),
                                   ep(5), ep(6, Status.PROCESSED)]),
         anime=anime(AnimeStatus.FINISHED, episodes=5),
         expected_result=stats(latest=5, total=4, processed=1, downloading=1, failed=1, covered={2})),
    Case(id="every downloading status counts as downloading",
         tracked_anime=tracked(1, [ep(1, Status.PENDING), ep(2, Status.DOWNLOADING),
                                   ep(3, Status.DOWNLOADED), ep(4, Status.PROCESSING)]),
         anime=anime(AnimeStatus.FINISHED, episodes=4),
         expected_result=stats(latest=4, total=4, downloading=4)),
    Case(id="every failed status counts as failed",
         tracked_anime=tracked(1, [ep(1, Status.FAILED_DOWNLOAD_INIT), ep(2, Status.FAILED_DOWNLOAD),
                                   ep(3, Status.FAILED_PROCESSING)]),
         anime=anime(AnimeStatus.FINISHED, episodes=3),
         expected_result=stats(latest=3, total=3, failed=3)),
    Case(id="deleted and discarded downloads are skipped for the next torrent",
         tracked_anime=tracked(1, [ep(1, Status.DELETED, Status.PROCESSED), ep(2, Status.DISCARDED)]),
         anime=anime(AnimeStatus.FINISHED, episodes=2),
         expected_result=stats(latest=2, total=2, processed=1, covered={1})),
    Case(id="first torrent with a download decides the bucket",
         tracked_anime=tracked(1, [ep(2, None, Status.FAILED_DOWNLOAD, Status.PROCESSED)]),
         anime=anime(AnimeStatus.FINISHED, episodes=12),
         expected_result=stats(latest=12, total=12, failed=1)),
    Case(id="covered episodes lists only processed episodes",
         tracked_anime=tracked(1, [ep(1, Status.PROCESSED), ep(2, Status.DOWNLOADING), ep(3, Status.PROCESSED)]),
         anime=anime(AnimeStatus.FINISHED, episodes=3),
         expected_result=stats(latest=3, total=3, processed=2, downloading=1, covered={1, 3})),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_get_episode_coverage_stats(case: Case):
    result = EpisodeComponent.__new__(EpisodeComponent).get_episode_coverage_stats(
        tracked_anime=case.tracked_anime, anime=case.anime, airing_schedule=case.airing_schedule)
    assert result == case.expected_result