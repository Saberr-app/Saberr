from datetime import timedelta, datetime, UTC

import aiofiles

from components.operational_components import BaseOperationalComponent
from components.operational_components.tracked_anime_component import TrackedAnimeComponent
from components.service_components.anilist_airing_schedule_component import AnilistAiringScheduleComponent
from components.service_components.anilist_component import AnilistComponent
from constants import AnilistAnimeStatus, TorrentDownloadStatus, AppAsset
from dto.anilist import AnilistAnime, AnilistAiringScheduleItem
from dto.anime_episode import EpisodeCoverageStats
from dto.orm_models import TrackedAnime
from services.discord_webhook_service import DiscordWebhookService
from utils.helpers.discord_webhook_helpers import construct_discord_webhook_payload_for_missing_episodes_report


class EpisodeComponent(BaseOperationalComponent):

    # noinspection PyMethodMayBeStatic
    def get_episode_coverage_stats(self,
                                   tracked_anime: TrackedAnime,
                                   anime: AnilistAnime,
                                   airing_schedule: list[AnilistAiringScheduleItem]) -> EpisodeCoverageStats:
        next_episode = min(schedule_item.episode for schedule_item in airing_schedule) if airing_schedule else None
        if anime.status == AnilistAnimeStatus.FINISHED \
                or (not airing_schedule and anime.end_date and anime.end_date.parsed_date()
                    and (anime.end_date.parsed_date() - timedelta(hours=8)).date()
                    <= datetime.now(UTC).date()):
            latest_known_episode_number = anime.episodes
        elif next_episode:
            latest_known_episode_number = next_episode - 1
        elif anime.status == AnilistAnimeStatus.NOT_YET_RELEASED:
            latest_known_episode_number = 0
        else:
            latest_known_episode_number = None

        processed_episode_count = downloading_episode_count = failed_episode_count = 0
        covered_episodes = set()
        for episode in tracked_anime.episodes:
            if episode.episode_number < tracked_anime.from_episode or \
                    (latest_known_episode_number and episode.episode_number > latest_known_episode_number):
                continue
            for torrent in episode.torrents:
                if torrent.effective_download is None:
                    continue
                if torrent.effective_download.status == TorrentDownloadStatus.PROCESSED:
                    processed_episode_count += 1
                    covered_episodes.add(episode.episode_number)
                    break
                elif torrent.effective_download.status in [TorrentDownloadStatus.PROCESSING,
                                                           TorrentDownloadStatus.DOWNLOADED,
                                                           TorrentDownloadStatus.DOWNLOADING,
                                                           TorrentDownloadStatus.PENDING]:
                    downloading_episode_count += 1
                    break
                elif torrent.effective_download.status in [TorrentDownloadStatus.FAILED_PROCESSING,
                                                           TorrentDownloadStatus.FAILED_DOWNLOAD,
                                                           TorrentDownloadStatus.FAILED_DOWNLOAD_INIT]:
                    failed_episode_count += 1
                    break

        return EpisodeCoverageStats(
            latest_known_episode_number=latest_known_episode_number,
            processed_episode_count=processed_episode_count,
            downloading_episode_count=downloading_episode_count,
            failed_episode_count=failed_episode_count,
            total_episode_count=max(latest_known_episode_number - tracked_anime.from_episode + 1, 0)
            if latest_known_episode_number else None,
            covered_episodes=covered_episodes
        )

    async def send_tracked_anime_episode_coverage_report(self):
        tracked_anime_records = await TrackedAnimeComponent().get_all_tracked_anime()
        anilist_anime_records = await AnilistComponent().get_anime_records(anilist_anime_ids=[
            tracked_anime.anilist_id for tracked_anime in tracked_anime_records
        ])
        anilist_anime_id_anime_map = {anilist_anime.id: anilist_anime for anilist_anime in anilist_anime_records}
        airing_map = await AnilistAiringScheduleComponent().get_future_anime_schedule_records_map(
            anilist_id_status_map={anime.id: anime.status for anime in anilist_anime_records},
            force_fetch=True
        )

        tracked_anime_coverage_stats_map = {
            tracked_anime: self.get_episode_coverage_stats(
                tracked_anime=tracked_anime,
                anime=anilist_anime_id_anime_map.get(tracked_anime.anilist_id),
                airing_schedule=airing_map.get(tracked_anime.anilist_id)
            )
            for tracked_anime in tracked_anime_records
        }

        if not any(coverage_stats.has_unprocessed() for coverage_stats in tracked_anime_coverage_stats_map.values()):
            return

        discord_payload = construct_discord_webhook_payload_for_missing_episodes_report(
            tracked_anime_coverage_stats_map=tracked_anime_coverage_stats_map,
        )
        async with aiofiles.open(AppAsset.ICON, 'rb') as icon_file:
            await DiscordWebhookService().send_notification(
                payload=discord_payload, author_png_image=await icon_file.read()
            )
