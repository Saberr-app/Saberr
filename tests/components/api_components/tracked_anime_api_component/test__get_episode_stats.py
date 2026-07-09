from dataclasses import dataclass, field
from datetime import datetime, UTC
from types import SimpleNamespace

import pytest

from api.schemas.tracked_anime_schemas import TrackedAnimeItem
from components.api_components.tracked_anime_api_component import TrackedAnimeAPIComponent
from constants import AnilistAnimeStatus as AnimeStatus, TorrentDownloadStatus as Status

Stats = TrackedAnimeItem.EpisodeStats

# parsed_date() is only consulted for a RELEASING anime with no airing schedule; a clearly past date
# reads as "ended", a far-future one as "still going".
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


@dataclass
class Case:
    id: str
    tracked_anime: object
    anime: object
    expected_result: Stats
    airing_schedule: list = field(default_factory=list)


CASES = [
    # --- latest_known_episode_number derivation (no episodes, so counts are all zero) ---
    Case(id="finished anime uses total episode count",
         tracked_anime=tracked(1, []), anime=anime(AnimeStatus.FINISHED, episodes=12),
         expected_result=Stats(latest_known_episode_number=12, processed_episode_count=0,
                               downloading_episode_count=0, failed_episode_count=0)),
    # soonest airing episode minus one is the latest already-aired episode
    Case(id="airing schedule sets latest to next episode minus one",
         tracked_anime=tracked(1, []), anime=anime(AnimeStatus.RELEASING),
         airing_schedule=schedule(7, 5),
         expected_result=Stats(latest_known_episode_number=4, processed_episode_count=0,
                               downloading_episode_count=0, failed_episode_count=0)),
    Case(id="not-yet-released anime has zero known episodes",
         tracked_anime=tracked(1, []), anime=anime(AnimeStatus.NOT_YET_RELEASED),
         expected_result=Stats(latest_known_episode_number=0, processed_episode_count=0,
                               downloading_episode_count=0, failed_episode_count=0)),
    Case(id="releasing with no schedule and no end date is unknown",
         tracked_anime=tracked(1, []), anime=anime(AnimeStatus.RELEASING, end_date=None),
         expected_result=Stats(latest_known_episode_number=None, processed_episode_count=0,
                               downloading_episode_count=0, failed_episode_count=0)),
    # a past end date (minus 8h) counts the anime as finished airing
    Case(id="releasing but past end date uses total episode count",
         tracked_anime=tracked(1, []), anime=anime(AnimeStatus.RELEASING, episodes=12, end_date=_PAST_END),
         expected_result=Stats(latest_known_episode_number=12, processed_episode_count=0,
                               downloading_episode_count=0, failed_episode_count=0)),
    Case(id="future end date stays unknown",
         tracked_anime=tracked(1, []), anime=anime(AnimeStatus.RELEASING, end_date=_FUTURE_END),
         expected_result=Stats(latest_known_episode_number=None, processed_episode_count=0,
                               downloading_episode_count=0, failed_episode_count=0)),

    # --- counting, honouring from_episode and the latest-known upper bound ---
    # from_episode=2 drops ep1; latest_known=5 (finished) drops ep6; ep5 has no download
    Case(id="counts within window; below-from and above-latest are skipped",
         tracked_anime=tracked(2, [ep(1, Status.PROCESSED), ep(2, Status.PROCESSED),
                                   ep(3, Status.DOWNLOADING), ep(4, Status.FAILED_PROCESSING),
                                   ep(5), ep(6, Status.PROCESSED)]),
         anime=anime(AnimeStatus.FINISHED, episodes=5),
         expected_result=Stats(latest_known_episode_number=5, processed_episode_count=1,
                               downloading_episode_count=1, failed_episode_count=1)),
    # the first torrent with an effective download decides the episode's bucket
    Case(id="first torrent with a download decides the bucket",
         tracked_anime=tracked(1, [ep(2, Status.FAILED_DOWNLOAD, Status.PROCESSED)]),
         anime=anime(AnimeStatus.FINISHED, episodes=12),
         expected_result=Stats(latest_known_episode_number=12, processed_episode_count=0,
                               downloading_episode_count=0, failed_episode_count=1)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__get_episode_stats(case: Case):
    result = TrackedAnimeAPIComponent._get_episode_stats(
        tracked_anime=case.tracked_anime, anime=case.anime, airing_schedule=case.airing_schedule)
    assert result == case.expected_result
