from collections import defaultdict
from datetime import datetime
from pathlib import Path

from api.schemas.download_schemas import DownloadListRequest, DownloadListResponse, DownloadItem, \
    DownloadUpdatesStreamResponse, DownloadRetryCheck, DeleteDownloadRequest
from common.context_helpers import thread_out
from common.db import get_session
from common.decorators import require_db_session, api_component
from common.exceptions import NotFoundException, ValidationException
from components import BaseComponent
from components.service_components.qbit_component import QBitComponent
from components.operational_components.torrent_download_component import TorrentDownloadComponent
from components.operational_components.torrent_component import TorrentComponent
from constants import TorrentDownloadStatus
from dto.nyaa_item import NyaaItem
from dto.orm_models import TorrentDownload, Torrent
from dto.qbit import QBitTorrent
from repositories.torrent_repositories.torrent_download_repo import TorrentDownloadRepo
from repositories.torrent_repositories.torrent_repo import TorrentRepo


class DownloadAPIComponent(BaseComponent):

    def __init__(self):
        super().__init__()
        self._download_component = TorrentDownloadComponent()
        self._qbit_component = QBitComponent()
        self._torrent_component = TorrentComponent()

    @api_component
    async def get_downloads(self, params: DownloadListRequest) -> DownloadListResponse:
        downloads = await self._download_component.get_downloads(statuses=params.statuses,
                                                                 offset=params.offset,
                                                                 limit=params.limit)
        other_torrents = await TorrentRepo(get_session()).get_torrents_by_parent_ids(
            parent_ids={download.torrent_id for download in downloads}, load_relations=True
        )
        magnet_hash_latest_effective_download_time_map = await \
            self._download_component.get_magnet_hash_latest_effective_download_time_map(
                db_torrents=[download.torrent for download in downloads] + other_torrents,
            )
        download_id_other_torrents_map = defaultdict(list)
        for other_torrent in other_torrents:
            if not other_torrent.download:
                download_id_other_torrents_map[other_torrent.parent_torrent_id].append(other_torrent)
        try:
            qbit_torrents = await self._qbit_component.get_torrents(
                magnet_hashes={download.torrent.magnet_hash for download in downloads},
            )
            qbit_hash_qbit_torrent_map = {qt.hash: qt for qt in qbit_torrents}
        except Exception as e:
            self.logger.warning(f"Failed to get QBit torrents: {e}")
            qbit_hash_qbit_torrent_map = {}
        return DownloadListResponse(
            downloads=[
                self._to_download_item(
                    download=download,
                    other_torrents=download_id_other_torrents_map[download.torrent_id],
                    qbit_torrent=qbit_hash_qbit_torrent_map.get(download.torrent.magnet_hash),
                    latest_sibling_download_effective_time=magnet_hash_latest_effective_download_time_map.get(
                        download.torrent.magnet_hash
                    ),
                ) for download in downloads
            ]
        )

    @api_component
    async def get_download(self, download_id: int) -> DownloadItem:
        download = await self._download_component.get_download(download_id=download_id)
        if not download:
            raise NotFoundException(f"Download with ID {download_id} not found")
        other_torrents = await TorrentRepo(get_session()).get_torrents_by_parent_ids(
            parent_ids={download.torrent.id}, load_relations=True
        )
        other_torrents = [other_torrent for other_torrent in other_torrents if not other_torrent.download]
        magnet_hash_latest_effective_download_time_map = await \
            self._download_component.get_magnet_hash_latest_effective_download_time_map(
                db_torrents=[download.torrent] + other_torrents,
            )
        try:
            qbit_torrents = await self._qbit_component.get_torrents(magnet_hashes={download.torrent.magnet_hash})
            qbit_torrent = qbit_torrents[0] if qbit_torrents else None
        except Exception as e:
            self.logger.warning(f"Failed to get QBit torrents: {e}")
            qbit_torrent = None
        return self._to_download_item(
            download=download,
            other_torrents=other_torrents,
            qbit_torrent=qbit_torrent,
            latest_sibling_download_effective_time=magnet_hash_latest_effective_download_time_map.get(
                download.torrent.magnet_hash
            )
        )

    @staticmethod
    def _to_download_item(download: TorrentDownload,
                          other_torrents: list[Torrent],
                          qbit_torrent: QBitTorrent | None,
                          latest_sibling_download_effective_time: datetime | None) -> DownloadItem:
        torrent = download.torrent
        tracked_anime = torrent.tracked_anime_episode.tracked_anime
        nyaa_item = NyaaItem.from_xml_string(torrent.rss_xml)

        episode_numbers = {torrent.tracked_anime_episode.episode_number}
        episode_numbers.update(other_torrent.tracked_anime_episode.episode_number for other_torrent in other_torrents)

        superseded = latest_sibling_download_effective_time is not None \
            and download.copied_to_destination_path_at is not None \
            and download.copied_to_destination_path_at < latest_sibling_download_effective_time

        return DownloadItem(
            id=download.id,
            status=download.status,
            status_details=download.status_details,
            download_directory_path=download.download_directory_path,
            source_path=download.source_path,
            destination_path=download.destination_path,
            copied_to_destination_path_at=download.copied_to_destination_path_at,
            created_at=download.created_at,
            superseded=superseded,
            anime=DownloadItem.Anime(
                anilist_id=tracked_anime.anilist_id,
                tracked_anime_id=tracked_anime.id,
                anilist_english_title=tracked_anime.english_title,
                anilist_native_title=tracked_anime.native_title,
                anilist_romaji_title=tracked_anime.romaji_title,
            ),
            anilist_episode_numbers=sorted(episode_numbers),
            anilist_episode_part=torrent.episode_part,
            anilist_episode_part_ceiling=torrent.episode_part_ceiling,
            torrent=DownloadItem.Torrent(
                id=torrent.id,
                web_link=nyaa_item.web_link,
                magnet_hash=torrent.magnet_hash,
                release_group=torrent.release_group,
                title=torrent.torrent_title,
                size=nyaa_item.size_str,
                encoding=torrent.encoding,
                resolution=torrent.resolution,
                source=torrent.source,
                language_code=torrent.language_code,
                version_number=torrent.version_number,
                repack_indicator=torrent.repack_indicator,
            ),
            qbit_status=DownloadItem.QBitStatus(
                status=qbit_torrent.state,
                progress=qbit_torrent.progress,
                eta=qbit_torrent.eta,
            ) if qbit_torrent else None,
        )

    @api_component
    async def check_download_retry(self, download_id: int) -> DownloadRetryCheck:
        download = await self._download_component.get_download(download_id=download_id)
        if not download:
            raise NotFoundException(f"Download with ID {download_id} not found")
        if newer_downloads := await TorrentDownloadRepo(get_session()).get_active_downloads_by_episode_id_and_part(
                tracked_anime_episode_id=download.torrent.tracked_anime_episode_id,
                episode_part=download.torrent.episode_part,
                episode_part_ceiling=download.torrent.episode_part_ceiling,
                exclude_download_ids=[download.id],
                created_at_after=download.created_at,
                created_at_tiebreak_id=download.id
        ):
            best_candidate = self._torrent_component.get_best_torrent_for_episode(
                db_torrents=newer_downloads + [download.torrent],
                anime_profile=download.torrent.tracked_anime_episode.tracked_anime.profile
            )
            if best_candidate and best_candidate.id != download.id:
                return DownloadRetryCheck(superseded=True)
        return DownloadRetryCheck(superseded=False)

    @api_component
    async def retry_download(self, download_id: int):
        download = await self._download_component.get_download(download_id=download_id)
        if not download:
            raise NotFoundException(f"Download with ID {download_id} not found")
        if download.status not in [TorrentDownloadStatus.FAILED_DOWNLOAD_INIT,
                                   TorrentDownloadStatus.FAILED_DOWNLOAD,
                                   TorrentDownloadStatus.FAILED_PROCESSING,
                                   TorrentDownloadStatus.DELETED,
                                   TorrentDownloadStatus.DISCARDED]:
            raise ValidationException(f"Download cannot be retried in status {download.status.value}")
        downloads = await self._download_component.get_downloads_by_hashes(magnet_hashes=[download.torrent.magnet_hash],
                                                                           load_relations=True)
        await TorrentDownloadRepo(get_session()).update_downloads(
            download_ids=[download.id for download in downloads],
            status=TorrentDownloadStatus.PENDING,
            status_retry_count=downloads[0].status_retry_count + 1,
            status_details=None
        )
        torrent_tags, category = await self._download_component.get_torrent_tags_and_category(downloads[0].torrent)
        try:
            qbit_torrent = await self._download_component.send_download_to_qbit(
                torrent_link=downloads[0].torrent.torrent_link,
                magnet_hash=downloads[0].torrent.magnet_hash,
                save_path=downloads[0].download_directory_path,
                category=category,
                torrent_tags=torrent_tags,
                resume_on_add=True
            )
        except Exception as e:
            self.logger.debug(f"Error while sending torrent download to qbit: {e}", exc_info=True)
            await TorrentDownloadRepo(get_session()).update_downloads(
                download_ids=[download.id for download in downloads],
                status=TorrentDownloadStatus.FAILED_DOWNLOAD_INIT,
                status_details=f"Error while sending torrent download to qbit: {e}",
                status_retry_count=downloads[0].status_retry_count + 1
            )
        else:
            await TorrentDownloadRepo(get_session()).update_downloads(
                download_ids=[download.id for download in downloads],
                status=TorrentDownloadStatus.DOWNLOADING,
                download_directory_path=qbit_torrent.save_path,
                status_retry_count=0,
                status_details=None
            )

    @api_component
    async def delete_download(self, download_id: int, body: DeleteDownloadRequest):
        download = await self._download_component.get_download(download_id=download_id)
        if not download:
            raise NotFoundException(f"Download with ID {download_id} not found")
        if body.discard_torrent:
            magnet_hash = download.torrent.magnet_hash
            await TorrentRepo(get_session()).update_torrents_by_magnet_hashes(magnet_hashes=[magnet_hash],
                                                                              discarded=True)
        if body.delete_imported_file:
            try:
                await thread_out(Path(download.destination_path).unlink, missing_ok=True)
            except Exception as e:
                self.logger.warning(f"Error while deleting imported file: {e}", exc_info=True)
        await self._download_component.delete_downloads_by_magnet_hashes(magnet_hashes=[download.torrent.magnet_hash],
                                                                         delete_from_qbit=body.delete_from_qbit,
                                                                         delete_from_disk=body.delete_from_disk)

    @require_db_session
    @api_component
    async def get_download_updates_stream(self, ref: int, download_ids: set[int]) -> DownloadUpdatesStreamResponse:
        downloads = await self._download_component.get_downloads(download_ids=download_ids)
        processed_download_ids = {download.id for download in downloads
                                  if download.status == TorrentDownloadStatus.PROCESSED}
        all_download_ids = {download.id for download in downloads}
        deleted_download_ids = download_ids - all_download_ids
        for download_id in processed_download_ids | deleted_download_ids:
            download_ids.discard(download_id)  # discard this download from passed mutable set for future stream events
        qbit_torrents = await self._qbit_component.get_torrents(magnet_hashes={download.torrent.magnet_hash
                                                                               for download in downloads})
        qbit_hash_qbit_torrent_map = {qt.hash: qt for qt in qbit_torrents}
        return DownloadUpdatesStreamResponse(
            ref=ref,
            changed=[
                DownloadUpdatesStreamResponse.DownloadStreamItem(
                    id=download.id,
                    status=download.status,
                    status_details=download.status_details,
                    download_directory_path=download.download_directory_path,
                    source_path=download.source_path,
                    destination_path=download.destination_path,
                    copied_to_destination_path_at=download.copied_to_destination_path_at,
                    qbit_status=qbit_hash_qbit_torrent_map[download.torrent.magnet_hash].state
                    if qbit_hash_qbit_torrent_map.get(download.torrent.magnet_hash) else None,
                    qbit_progress=qbit_hash_qbit_torrent_map[download.torrent.magnet_hash].progress
                    if qbit_hash_qbit_torrent_map.get(download.torrent.magnet_hash) else None,
                    qbit_eta=qbit_hash_qbit_torrent_map[download.torrent.magnet_hash].eta
                    if qbit_hash_qbit_torrent_map.get(download.torrent.magnet_hash) else None,
                ) for download in downloads
            ] + [
                DownloadUpdatesStreamResponse.DownloadStreamItem(
                    id=download_id,
                    deleted=True,
                ) for download_id in deleted_download_ids
            ]
        )

    @staticmethod
    def nullify_unchanged(old: DownloadUpdatesStreamResponse | None, new: DownloadUpdatesStreamResponse):
        if old is None:
            return
        old_downloads_map = {download.id: download for download in old.changed}
        new_downloads = []
        for download in new.changed:
            if download.id not in old_downloads_map or download != old_downloads_map[download.id]:
                new_downloads.append(download)
        new.changed = new_downloads
