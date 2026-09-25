from dataclasses import dataclass

import pytest

from config import config
from dto.anime_episode import EpisodeCoverageStats
from dto.orm_models import TrackedAnime
from utils.helpers.discord_webhook_helpers import construct_discord_webhook_payload_for_missing_episodes_report
from utils.helpers.text_helpers import shorten_text

_OVERFLOW_VALUE = "Go to your Tracked Anime page for an overview of all tracked anime and coverage status."


def tracked(tracked_anime_id, title=None):
    tracked_anime = TrackedAnime(romaji_title=title or f"Show {tracked_anime_id}")
    tracked_anime.id = tracked_anime_id
    return tracked_anime


def stats(total, processed=0, downloading=0, failed=0):
    return EpisodeCoverageStats(latest_known_episode_number=total, processed_episode_count=processed,
                                downloading_episode_count=downloading, failed_episode_count=failed,
                                total_episode_count=total, covered_episodes=set())


def field(name, value):
    return {"name": name, "value": value, "inline": False}


def unprocessed_fields(count):
    return [field(f"Show {i}", "**3** missing episodes\n") for i in range(1, count + 1)]


@dataclass
class Case:
    id: str
    coverage_stats_map: dict[TrackedAnime, EpisodeCoverageStats]
    expected_fields: list[dict]
    published_url: str | None = None


_LONG_TITLE = "x" * 300

CASES = [
    Case(id="empty map has no fields", coverage_stats_map={}, expected_fields=[]),
    Case(id="fully processed anime is skipped",
         coverage_stats_map={tracked(1): stats(total=5, processed=5)}, expected_fields=[]),
    Case(id="unknown total is skipped",
         coverage_stats_map={tracked(1): stats(total=None)}, expected_fields=[]),
    Case(id="missing episodes only",
         coverage_stats_map={tracked(1): stats(total=5, processed=2)},
         expected_fields=[field("Show 1", "**3** missing episodes\n")]),
    Case(id="missing, downloading and failed lines in order",
         coverage_stats_map={tracked(1): stats(total=10, processed=4, downloading=2, failed=1)},
         expected_fields=[field("Show 1", "**3** missing episodes\n"
                                          "**2** downloading episodes\n"
                                          "**1** failed episodes\n")]),
    Case(id="zero-count lines are omitted",
         coverage_stats_map={tracked(1): stats(total=3, processed=1, failed=2)},
         expected_fields=[field("Show 1", "**2** failed episodes\n")]),
    Case(id="only unprocessed anime get fields",
         coverage_stats_map={tracked(1): stats(total=5, processed=5), tracked(2): stats(total=5, processed=2)},
         expected_fields=[field("Show 2", "**3** missing episodes\n")]),
    Case(id="published url adds a link to the tracked anime page",
         coverage_stats_map={tracked(7): stats(total=5, processed=2)}, published_url="http://host/",
         expected_fields=[field("Show 7", "**3** missing episodes\n[Go to ›](http://host/tracked/7)\n")]),
    Case(id="long titles are shortened",
         coverage_stats_map={tracked(1, title=_LONG_TITLE): stats(total=5, processed=2)},
         expected_fields=[field(shorten_text(_LONG_TITLE, 250), "**3** missing episodes\n")]),
    Case(id="twenty-five unprocessed anime all fit",
         coverage_stats_map={tracked(i): stats(total=5, processed=2) for i in range(1, 26)},
         expected_fields=unprocessed_fields(25)),
    Case(id="more than twenty-five unprocessed anime are cut with an overflow field",
         coverage_stats_map={tracked(i): stats(total=5, processed=2) for i in range(1, 31)},
         expected_fields=unprocessed_fields(24) + [field("... and 6 more", _OVERFLOW_VALUE)]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_construct_discord_webhook_payload_for_missing_episodes_report(case: Case):
    config.user_settings.published_url = case.published_url

    payload = construct_discord_webhook_payload_for_missing_episodes_report(
        tracked_anime_coverage_stats_map=case.coverage_stats_map)

    assert list(payload.keys()) == ["embeds"]
    assert len(payload["embeds"]) == 1
    embed = payload["embeds"][0]
    assert embed["title"] == "Missing episodes report"
    assert embed["author"] == {"name": "Saberr"}
    assert embed["fields"] == case.expected_fields