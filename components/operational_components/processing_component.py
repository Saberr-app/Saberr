import shutil
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Coroutine

import aiofiles

from common.context_helpers import thread_out
from common.db import get_session
from common.decorators import require_db_session, suppress_and_log
from common.exceptions import PreprocessingFailedException, TVDBIncompleteDataException
from components.operational_components import BaseOperationalComponent
from components.service_components.anilist_component import AnilistComponent
from components.service_components.qbit_component import QBitComponent
from components.service_components.tvdb_component import TVDBComponent
from config import config
from constants import TorrentDownloadStatus, AuditLogCode, AppAsset
from dto.anilist import AnilistAnime
from dto.orm_models import TorrentDownload, Torrent
from dto.qbit import QBitTorrent
from dto.tvdb import TVDBSeriesEpisode
from app_state import global_status
from repositories.torrent_repositories.torrent_download_repo import TorrentDownloadRepo
from repositories.torrent_repositories.torrent_repo import TorrentRepo
from services.discord_webhook_service import DiscordWebhookService
from utils.helpers.discord_webhook_helpers import construct_discord_webhook_payload_for_processing_finished
from utils.helpers.file_name_formatters import format_season_directory_name, format_file_name


class ProcessingComponent(BaseOperationalComponent):

    def __init__(self):
        from components.operational_components.tracked_anime_episode_component import TrackedAnimeEpisodeComponent
        super().__init__()
        self._tracked_anime_episode_component = TrackedAnimeEpisodeComponent()

    async def initiate_download_processing(self,
                                           torrent_downloads: list[TorrentDownload],
                                           qbit_torrent: QBitTorrent) -> tuple[Path, Path, Coroutine]:
        self.logger.debug(f"Initiating download processing for torrent {torrent_downloads[0].torrent.torrent_title}")
        video_file_path, related_file_paths = await thread_out(
            QBitComponent.find_download_files, qbit_torrent=qbit_torrent
        )
        if not video_file_path:
            raise PreprocessingFailedException(f"No video file found in torrent: {qbit_torrent.name}")
        tracked_anime = torrent_downloads[0].torrent.tracked_anime_episode.tracked_anime
        anilist_anime = await AnilistComponent().get_anime(anilist_anime_id=tracked_anime.anilist_id)
        tvdb_series, tvdb_episodes = None, []
        if tracked_anime.tvdb_structure_enabled:
            try:
                tracked_anime_episodes = []
                for torrent_download in torrent_downloads:  # force refresh TVDB episode ids
                    tracked_anime_episode = \
                        await self._tracked_anime_episode_component.get_or_create_tracked_anime_episode(
                            episode_number=torrent_download.torrent.tracked_anime_episode.episode_number,
                            tracked_anime=tracked_anime,
                            tvdb_data_freshness_minimum=timedelta(minutes=5),
                            raise_on_tvdb_unavailability=True
                        )
                    tracked_anime_episodes.append(tracked_anime_episode)
                if not (tvdb_series_id := tracked_anime_episodes[0].tvdb_series_id):
                    raise TVDBIncompleteDataException(f"No TVDB series ID found for episode "
                                                      f"{tracked_anime_episodes[0].episode_number}")
                tvdb_series_episodes = await TVDBComponent().get_series_episodes(
                    series_id=tvdb_series_id,
                    season_type=tracked_anime.tvdb_season_type,
                    minimum_freshness=timedelta(minutes=6)
                )
                tvdb_episode_ids = {
                    tvdb_episode_id
                    for tracked_anime_episode in tracked_anime_episodes
                    for tvdb_episode_id in tracked_anime_episode.tvdb_episode_ids
                }
                tvdb_episodes = [tvdb_episode for tvdb_episode in tvdb_series_episodes.episodes
                                 if tvdb_episode.id in tvdb_episode_ids]
                tvdb_series = await TVDBComponent().get_series(series_id=tvdb_series_id,
                                                               minimum_freshness=timedelta(weeks=2))
                if len(tvdb_episodes) != len(tvdb_episode_ids):
                    raise TVDBIncompleteDataException(f"Not all TVDB episodes were found in this season type")
            except TVDBIncompleteDataException:
                raise
            except Exception as e:
                raise PreprocessingFailedException(f"Failed to collect all required TVDB data: {e}") from e
        target_directory = Path(tracked_anime.show_parent_directory).resolve() / tracked_anime.show_folder_name
        if tracked_anime.tvdb_structure_enabled:
            target_directory /= format_season_directory_name(processing_settings=tracked_anime.processing_settings,
                                                             season_number=tvdb_episodes[0].season_number)
        target_file_name = format_file_name(tracked_anime=tracked_anime,
                                            anilist_anime=anilist_anime,
                                            tvdb_show=tvdb_series,
                                            tvdb_episodes=tvdb_episodes,
                                            db_torrents=[download.torrent for download in torrent_downloads])
        existing_files = await self._get_existing_processed_file_paths(
            # any processed torrent that shares the same "space"
            tracked_anime_episode_id=torrent_downloads[0].torrent.tracked_anime_episode_id,
            episode_part=torrent_downloads[0].torrent.episode_part,
            episode_part_ceiling=torrent_downloads[0].torrent.episode_part_ceiling
        )
        return (target_directory / (target_file_name + Path(video_file_path).suffix),
                video_file_path,
                self._finalize_download_processing(torrent_download_ids=[torrent_download.id
                                                                         for torrent_download
                                                                         in torrent_downloads],
                                                   magnet_hash=qbit_torrent.hash,
                                                   target_directory=target_directory,
                                                   target_file_name=target_file_name,
                                                   source_video_file_path=video_file_path,
                                                   source_related_file_paths=related_file_paths,
                                                   existing_files=existing_files,
                                                   anilist_anime=anilist_anime,
                                                   tvdb_episodes=tvdb_episodes, ))

    @staticmethod
    async def _get_existing_processed_file_paths(tracked_anime_episode_id: int,
                                                 episode_part: int, episode_part_ceiling: int) -> list[Path]:
        torrent_downloads = await TorrentDownloadRepo(get_session()).get_by_episode_id_and_part(
            tracked_anime_episode_id=tracked_anime_episode_id,
            episode_part=episode_part,
            episode_part_ceiling=episode_part_ceiling,
            processed_only=True
        )
        paths = []
        for torrent_download in torrent_downloads:
            if torrent_download.destination_path:
                paths.append(Path(torrent_download.destination_path).resolve())
        return paths

    @require_db_session
    async def _finalize_download_processing(self,
                                            torrent_download_ids: list[int],
                                            magnet_hash: str,
                                            target_directory: Path,
                                            target_file_name: str,
                                            source_video_file_path: Path,
                                            source_related_file_paths: list[Path],
                                            existing_files: list[Path],
                                            anilist_anime: AnilistAnime,
                                            tvdb_episodes: list[TVDBSeriesEpisode]):
        target_video_path = target_directory / (target_file_name + source_video_file_path.suffix)
        self.logger.debug(f"Finalizing download processing for {target_video_path}")
        try:
            await thread_out(self._copy_file, source_video_file_path, target_video_path)
        except Exception as e:
            self.logger.debug(f"Failed to copy video file to {target_video_path} for downloads "
                              f"{torrent_download_ids}: {e}", exc_info=True)
            await self._set_post_processing_status(succeeded=False, torrent_download_ids=torrent_download_ids, error=e)
        else:
            await self._set_post_processing_status(succeeded=True, torrent_download_ids=torrent_download_ids)
            try:
                await thread_out(self._replace_existing_files,
                                 existing_files,
                                 target_file_name,
                                 target_video_path)
                await thread_out(self._copy_related_files, source_related_file_paths, source_video_file_path,
                                 target_directory, target_file_name)
            except Exception as e:
                self.logger.warning(f"Failed to replace existing files or copy related files for downloads "
                                    f"{torrent_download_ids}: {e}", exc_info=True)
            if config.user_settings.notifications_discord_webhook_url and \
                    ((config.user_settings.discord_notify_on_download_processed and not bool(existing_files)) or
                     (config.user_settings.discord_notify_on_upgrade_download_processed and bool(existing_files))):
                await self._send_discord_notifications(magnet_hash=magnet_hash,
                                                       anilist_anime=anilist_anime,
                                                       tvdb_episodes=tvdb_episodes,
                                                       is_upgrade=bool(existing_files))

    @staticmethod
    def _copy_file(source: Path, target: Path):
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    def _replace_existing_files(self, existing_files: list[Path], new_stem: str, target_video_path: Path):
        for existing_file in existing_files:
            directory = existing_file.parent
            old_stem = existing_file.stem
            if not directory.exists():
                continue
            for sibling in directory.iterdir():
                if sibling.name != old_stem and not sibling.name.startswith(old_stem + "."):
                    continue
                if sibling.resolve() == target_video_path.resolve():
                    continue
                if sibling == existing_file:
                    try:
                        sibling.unlink()
                    except Exception as e:
                        self.logger.warning(f"Failed to delete existing file {sibling}: {e}", exc_info=True)
                    continue
                renamed = directory / (new_stem + sibling.name[len(old_stem):])
                if renamed.resolve() == sibling.resolve():
                    continue
                try:
                    sibling.replace(renamed)
                except Exception as e:
                    self.logger.debug(f"Failed to rename {sibling} to {renamed}: {e}", exc_info=True)

    def _copy_related_files(self, source_related_file_paths: list[Path], source_video_file_path: Path,
                            target_directory: Path, new_stem: str):
        source_stem = source_video_file_path.stem
        for source_related_file_path in source_related_file_paths:
            name = source_related_file_path.name
            if name == source_stem or name.startswith(source_stem + "."):
                remainder = name[len(source_stem):]
            else:
                remainder = source_related_file_path.suffix
            target = target_directory / (new_stem + remainder)
            try:
                self._copy_file(source_related_file_path, target)
            except Exception as e:
                self.logger.debug(f"Failed to copy related file {source_related_file_path} to {target}: {e}",
                                  exc_info=True)

    # noinspection PyMethodMayBeStatic
    def _resolve_media_metadata(self, file_path: str) -> tuple[int | None, int | None, list[str]]:
        from pymediainfo import MediaInfo
        media_info = MediaInfo.parse(file_path)
        file_size, duration, audio_tracks = None, None, []
        for track in media_info.tracks:
            if track.track_type == "General":
                file_size = track.file_size
                if track.duration is not None:
                    duration = round(track.duration / 1000)
            elif track.track_type == "Audio" and track.language:
                audio_tracks.append(track.language)
        return file_size, duration, audio_tracks

    async def _set_post_processing_status(self,
                                          succeeded: bool,
                                          torrent_download_ids: list[int],
                                          error: Exception | None = None):
        torrent_downloads = await TorrentDownloadRepo(get_session()).get_downloads(download_ids=torrent_download_ids,
                                                                                   load_relations=True)
        audit_code = AuditLogCode.TORRENT_PROCESSING_FINISHED if succeeded else AuditLogCode.TORRENT_PROCESSING_FAILED
        status = TorrentDownloadStatus.PROCESSED if succeeded else TorrentDownloadStatus.FAILED_PROCESSING
        status_details = f"Failed to copy video file to destination: {error}" if not succeeded else None
        filter_by_statuses = [] if succeeded else [TorrentDownloadStatus.PROCESSING]
        copied_to_destination_path_at = datetime.now(UTC) if succeeded else None

        await TorrentDownloadRepo(get_session()).update_downloads(
            download_ids=[dl.id for dl in torrent_downloads],
            filter_by_statuses=filter_by_statuses,
            status=status,
            status_details=status_details,
            copied_to_destination_path_at=copied_to_destination_path_at
        )
        await self._audit_log_component.log_torrent_processing_action(code=audit_code,
                                                                      torrent_download=torrent_downloads[0],
                                                                      db_torrents=[dl.torrent
                                                                                   for dl in torrent_downloads])
        global_status.tracked_anime_updated()

    @suppress_and_log()
    async def _send_discord_notifications(self,
                                          magnet_hash: str,
                                          anilist_anime: AnilistAnime,
                                          tvdb_episodes: list[TVDBSeriesEpisode],
                                          is_upgrade: bool):
        torrent_download = await TorrentRepo(get_session()).get_torrents_by_hashes(magnet_hashes=[magnet_hash],
                                                                                   load_relations=True)
        for torrent in torrent_download:
            await self._send_discord_notification(torrent=torrent,
                                                  anilist_anime=anilist_anime,
                                                  tvdb_episodes=tvdb_episodes,
                                                  is_upgrade=is_upgrade)

    async def _send_discord_notification(self,
                                         torrent: Torrent,
                                         anilist_anime: AnilistAnime,
                                         tvdb_episodes: list[TVDBSeriesEpisode],
                                         is_upgrade: bool):
        try:
            file_size, duration, audio_tracks = await thread_out(
                self._resolve_media_metadata, torrent.effective_download.destination_path
            )
        except Exception as e:
            self.logger.debug(f"Failed to resolve media metadata for {torrent.effective_download.destination_path}: "
                              f"{e}", exc_info=True)
            file_size, duration, audio_tracks = None, None, [torrent.language_code]
        tvdb_episodes = [tvdb_episode for tvdb_episode in tvdb_episodes
                         if tvdb_episode.id in torrent.tracked_anime_episode.tvdb_episode_ids]
        webhook_payload = construct_discord_webhook_payload_for_processing_finished(
            anime_title=torrent.tracked_anime_episode.tracked_anime.preferred_title,
            anilist_id=torrent.tracked_anime_episode.tracked_anime.anilist_id,
            mal_id=anilist_anime.idMal,
            nyaa_id=torrent.nyaa_id,
            tvdb_series_id=torrent.tracked_anime_episode.tvdb_series_id,
            season_number=torrent.tracked_anime_episode.tvdb_season_number,
            anime_episode_number=torrent.tracked_anime_episode.episode_number,
            tvdb_episode_numbers=torrent.tracked_anime_episode.tvdb_episode_numbers,
            tvdb_episode_part=torrent.tracked_anime_episode.tvdb_episode_part,
            tvdb_episode_title=" / ".join([episode.title for episode in tvdb_episodes if episode.title]),
            tvdb_episode_overview=tvdb_episodes[0].overview if tvdb_episodes else None,
            destination_path=torrent.effective_download.destination_path,
            release_group=torrent.release_group,
            release_title=torrent.torrent_title,
            file_size_bytes=file_size,
            file_extension=torrent.effective_download.destination_path.rsplit('.', 1)[-1].upper(),
            resolution=torrent.resolution.value,
            encoding=torrent.encoding.value,
            resolved_audio_languages=audio_tracks,
            resolved_duration_seconds=duration,
            resolved_source=torrent.source.value,
            is_an_upgrade=is_upgrade,
            poster_url=anilist_anime.medium_cover_image,
            episode_image_url=tvdb_episodes[0].image_url if tvdb_episodes else None,
            banner_url=anilist_anime.banner_image,
            anilist_rating=anilist_anime.mean_score or None,
            time=torrent.effective_download.copied_to_destination_path_at
        )

        async with aiofiles.open(AppAsset.ICON, 'rb') as icon_file:
            await DiscordWebhookService().send_notification(
                payload=webhook_payload, author_png_image=await icon_file.read()
            )
