from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from components.operational_components import episode_component
from components.operational_components.episode_component import EpisodeComponent
from constants import AppAsset
from dto.anilist import AnilistAiringScheduleItem
from dto.anime_episode import EpisodeCoverageStats
from dto.orm_models import TrackedAnime
from tests.support.builders import make_airing, make_anime
from tests.support.mocks import patch_async_returns

_MODULE = "components.operational_components.episode_component"
_ICON_BYTES = b"\x89PNG"
_PAYLOAD = {"embeds": [{"author": {"name": "Saberr"}}]}


def tracked(tracked_anime_id, anilist_id):
    tracked_anime = TrackedAnime(anilist_id=anilist_id, romaji_title=f"Show {anilist_id}", from_episode=1)
    tracked_anime.id = tracked_anime_id
    return tracked_anime


def stats(total, processed):
    return EpisodeCoverageStats(latest_known_episode_number=total, processed_episode_count=processed,
                                downloading_episode_count=0, failed_episode_count=0,
                                total_episode_count=total, covered_episodes=set(range(1, processed + 1)))


@dataclass
class Case:
    id: str
    tracked_anime_records: list[TrackedAnime]
    coverage_stats: list[EpisodeCoverageStats]
    expect_sent: bool
    airing_map: dict[int, list[AnilistAiringScheduleItem]] = field(default_factory=dict)


CASES = [
    Case(id="no tracked anime sends nothing",
         tracked_anime_records=[], coverage_stats=[], expect_sent=False),
    Case(id="fully processed anime sends nothing",
         tracked_anime_records=[tracked(1, 101), tracked(2, 102)],
         coverage_stats=[stats(total=12, processed=12), stats(total=3, processed=3)],
         expect_sent=False),
    Case(id="unknown totals send nothing",
         tracked_anime_records=[tracked(1, 101)],
         coverage_stats=[stats(total=None, processed=0)],
         expect_sent=False),
    Case(id="one anime with unprocessed episodes sends the report",
         tracked_anime_records=[tracked(1, 101), tracked(2, 102)],
         coverage_stats=[stats(total=12, processed=12), stats(total=5, processed=3)],
         airing_map={102: [make_airing(airing_at=1, episode=6, anilist_id=102)]},
         expect_sent=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_send_tracked_anime_episode_coverage_report(case: Case, mocker):
    anilist_records = [make_anime(t.anilist_id, status="RELEASING") for t in case.tracked_anime_records]
    mocks = patch_async_returns(mocker, {
        f"{_MODULE}.TrackedAnimeComponent.get_all_tracked_anime": case.tracked_anime_records,
        f"{_MODULE}.AnilistComponent.get_anime_records": anilist_records,
        f"{_MODULE}.AnilistAiringScheduleComponent.get_future_anime_schedule_records_map": case.airing_map,
        f"{_MODULE}.DiscordWebhookService.send_notification": None,
    })
    get_stats = mocker.patch.object(EpisodeComponent, "get_episode_coverage_stats",
                                    side_effect=case.coverage_stats)
    build_payload = mocker.patch(f"{_MODULE}.construct_discord_webhook_payload_for_missing_episodes_report",
                                 return_value=_PAYLOAD)
    icon_handle = MagicMock()
    icon_handle.read = AsyncMock(return_value=_ICON_BYTES)
    aiofiles_open = MagicMock()
    aiofiles_open.return_value.__aenter__ = AsyncMock(return_value=icon_handle)
    aiofiles_open.return_value.__aexit__ = AsyncMock(return_value=False)
    mocker.patch.object(episode_component.aiofiles, "open", aiofiles_open)

    await EpisodeComponent().send_tracked_anime_episode_coverage_report()

    mocks[f"{_MODULE}.AnilistComponent.get_anime_records"].assert_awaited_once_with(
        anilist_anime_ids=[t.anilist_id for t in case.tracked_anime_records])
    mocks[f"{_MODULE}.AnilistAiringScheduleComponent.get_future_anime_schedule_records_map"].assert_awaited_once_with(
        anilist_id_status_map={anime.id: anime.status for anime in anilist_records}, force_fetch=True)
    assert get_stats.call_args_list == [
        call(tracked_anime=tracked_anime, anime=anime, airing_schedule=case.airing_map.get(tracked_anime.anilist_id))
        for tracked_anime, anime in zip(case.tracked_anime_records, anilist_records)
    ]

    send = mocks[f"{_MODULE}.DiscordWebhookService.send_notification"]
    if not case.expect_sent:
        build_payload.assert_not_called()
        send.assert_not_awaited()
        return

    build_payload.assert_called_once_with(tracked_anime_coverage_stats_map=dict(
        zip(case.tracked_anime_records, case.coverage_stats)))
    aiofiles_open.assert_called_once_with(AppAsset.ICON, 'rb')
    send.assert_awaited_once_with(payload=_PAYLOAD, author_png_image=_ICON_BYTES)