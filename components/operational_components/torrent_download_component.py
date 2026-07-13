from collections import defaultdict
from datetime import datetime, UTC, timedelta
from typing import Coroutine, Iterable

from common.db import get_session
from common.exceptions import ExternalServiceException, TVDBIncompleteDataException
from components.operational_components import BaseOperationalComponent
from components.service_components.qbit_component import QBitComponent
from config import config
from constants import TorrentDownloadStatus, DOWNLOAD_PROCESSING_RETRY_LIMIT, QBITTORRENT_UNFINISHED_STATES, \
    QBITTORRENT_ERROR_STATES, AuditLogCode
from dto.orm_models import TorrentDownload, Torrent
from dto.qbit import QBitTorrent
from app_state import global_status
from repositories.torrent_repositories.torrent_download_repo import TorrentDownloadRepo
from utils.helpers.text_helpers import get_human_readable_time


class TorrentDownloadComponent(BaseOperationalComponent):

    def __init__(self):
        from components.operational_components.processing_component import ProcessingComponent
        super().__init__()
        self._qbit_component = QBitComponent()
        self._processing_component = ProcessingComponent()

    # noinspection PyMethodMayBeStatic
    async def create_download(self,
                              torrent_id: int,
                              status: TorrentDownloadStatus,
                              download_directory_path: str,
                              destination_path: str | None = None,
                              status_retry_count: int = 0,
                              status_details: str | None = None,
                              copied_to_destination_path_at: datetime | None = None) -> TorrentDownload:
        download = await TorrentDownloadRepo(get_session()).create_download(
            torrent_id=torrent_id,
            status=status,
            status_retry_count=status_retry_count,
            status_details=status_details,
            download_directory_path=download_directory_path,
            destination_path=destination_path,
            copied_to_destination_path_at=copied_to_destination_path_at
        )
        global_status.download_added()
        return download

    # noinspection PyMethodMayBeStatic
    async def get_downloads(self,
                            download_ids: Iterable[int] | None = None,
                            statuses: list[TorrentDownloadStatus] | None = None,
                            offset: int | None = None,
                            limit: int | None = None,
                            load_relations: bool = True) -> list[TorrentDownload]:
        return await TorrentDownloadRepo(get_session()).get_downloads(download_ids=download_ids,
                                                                      offset=offset,
                                                                      limit=limit,
                                                                      statuses=statuses,
                                                                      sort_by=TorrentDownload.id.desc(),
                                                                      load_relations=load_relations)

    # noinspection PyMethodMayBeStatic
    async def get_downloads_by_hashes(self,
                                      magnet_hashes: list[str],
                                      load_relations: bool = True) -> list[TorrentDownload]:
        return await TorrentDownloadRepo(get_session()).get_downloads_by_hashes(magnet_hashes=magnet_hashes,
                                                                                load_relations=load_relations)

    # noinspection PyMethodMayBeStatic
    async def get_download(self, download_id: int,
                           load_relations: bool = True) -> TorrentDownload | None:
        return await TorrentDownloadRepo(get_session()).get_download(download_id=download_id,
                                                                     load_relations=load_relations)

    async def create_downloads_for_torrent(self,
                                           db_torrent_group: list[Torrent],
                                           download_directory_path: str | None) -> TorrentDownload:
        self.logger.info(f"Creating downloads for torrent {db_torrent_group[0].torrent_title} "
                         f"({db_torrent_group[0].magnet_hash})")
        await self._audit_log_component.log_torrent_selected_action(db_torrents=db_torrent_group,
                                                                    download_directory_path=download_directory_path)
        torrent_download_repo = TorrentDownloadRepo(get_session())
        parent_db_torrent = [db_torrent for db_torrent
                             in db_torrent_group if db_torrent.parent_torrent_id is None][0]
        download = await self.create_download(
            torrent_id=parent_db_torrent.id,
            status=TorrentDownloadStatus.PENDING,
            download_directory_path=download_directory_path,
        )
        torrent_tags, category = await self.get_torrent_tags_and_category(parent_db_torrent)
        try:
            qbit_torrent = await self.send_download_to_qbit(
                torrent_link=parent_db_torrent.torrent_link,
                magnet_hash=parent_db_torrent.magnet_hash,
                save_path=download_directory_path,
                category=category,
                torrent_tags=torrent_tags
            )
        except Exception as e:
            self.logger.debug(f"Error while sending torrent download to qbit: {e}", exc_info=True)
            await torrent_download_repo.update_downloads(
                download_ids=[download.id],
                status=TorrentDownloadStatus.FAILED_DOWNLOAD_INIT,
                status_details=f"Error while sending torrent download to qbit: {e}"
            )
            await self._audit_log_torrent_processing_action(download_status=TorrentDownloadStatus.FAILED_DOWNLOAD_INIT,
                                                            torrent_download=download,
                                                            db_torrents=db_torrent_group)
        else:
            await torrent_download_repo.update_downloads(
                download_ids=[download.id],
                status=TorrentDownloadStatus.DOWNLOADING,
                download_directory_path=qbit_torrent.save_path
            )
            await self._audit_log_torrent_processing_action(download_status=TorrentDownloadStatus.DOWNLOADING,
                                                            torrent_download=download,
                                                            db_torrents=db_torrent_group)
        return download

    async def send_download_to_qbit(self, torrent_link: str, magnet_hash: str, save_path: str | None, category: str,
                                    torrent_tags: list[str], resume_on_add: bool = False) -> QBitTorrent:
        qbit_torrent = await self._qbit_component.add_torrent(
            torrent_or_magnet_link=torrent_link,
            magnet_hash=magnet_hash,
            save_path=save_path,
            category=category,
            tags=torrent_tags,
            resume_on_add=resume_on_add
        )
        if not qbit_torrent:
            raise ExternalServiceException(f"Could not locate torrent after sending it to qbit with hash "
                                           f"{magnet_hash}")
        return qbit_torrent

    async def delete_downloads_by_magnet_hashes(self,
                                                magnet_hashes: list[str],
                                                delete_from_qbit: bool = False,
                                                delete_from_disk: bool = False):
        await TorrentDownloadRepo(get_session()).delete_downloads_by_magnet_hashes(magnet_hashes=magnet_hashes)
        if delete_from_qbit:
            await self._qbit_component.delete_torrents(magnet_hashes=magnet_hashes, delete_from_disk=delete_from_disk)
        global_status.tracked_anime_updated()

    async def advance_downloads_in_pre_downloading_status(self):
        torrent_download_repo = TorrentDownloadRepo(get_session())
        downloads = await torrent_download_repo.get_downloads(
            statuses=[TorrentDownloadStatus.FAILED_DOWNLOAD, TorrentDownloadStatus.FAILED_DOWNLOAD_INIT],
            retry_count_less_than=DOWNLOAD_PROCESSING_RETRY_LIMIT,
            updated_at_before=datetime.now(UTC) - timedelta(minutes=3),
            load_relations=True
        )
        downloads.extend(await torrent_download_repo.get_downloads(
            statuses=[TorrentDownloadStatus.PENDING],
            load_relations=True
        ))
        downloads = await self._filter_out_and_update_superseded_downloads(downloads=downloads)
        if not downloads:
            return

        hash_downloads_map: dict[str, list[TorrentDownload]] = defaultdict(list)
        for download in downloads:
            hash_downloads_map[download.torrent.magnet_hash].append(download)
        qbit_downloads = await self._qbit_component.get_torrents(magnet_hashes=hash_downloads_map.keys())
        hash_qbit_download_map = {
            qbit_download.hash: qbit_download for qbit_download in qbit_downloads
        }

        for hash_, downloads in hash_downloads_map.items():
            statuses_to_audit = [TorrentDownloadStatus.DELETED, TorrentDownloadStatus.DISCARDED,
                                 TorrentDownloadStatus.DOWNLOADING, TorrentDownloadStatus.DOWNLOADED]
            qbit_download = hash_qbit_download_map.get(hash_)
            download_status = self._resolve_torrent_download_qbit_status(qbit_download=qbit_download,
                                                                         current_status=downloads[0].status)
            if downloads[0].status == download_status \
                    and download_status in [TorrentDownloadStatus.FAILED_DOWNLOAD_INIT, TorrentDownloadStatus.PENDING]:
                torrent_tags, category = await self.get_torrent_tags_and_category(downloads[0].torrent)
                try:
                    qbit_torrent = await self.send_download_to_qbit(
                        torrent_link=downloads[0].torrent.torrent_link,
                        magnet_hash=downloads[0].torrent.magnet_hash,
                        save_path=downloads[0].download_directory_path,
                        category=category,
                        torrent_tags=torrent_tags
                    )
                except Exception as e:
                    self.logger.debug(f"Error while sending torrent download to qbit: {e}", exc_info=True)
                    await torrent_download_repo.update_downloads(
                        download_ids=[download.id for download in downloads],
                        status=TorrentDownloadStatus.FAILED_DOWNLOAD_INIT,
                        status_details=f"Error while sending torrent download to qbit: {e}",
                        status_retry_count=downloads[0].status_retry_count + 1
                    )
                else:
                    await torrent_download_repo.update_downloads(
                        download_ids=[download.id for download in downloads],
                        status=TorrentDownloadStatus.DOWNLOADING,
                        download_directory_path=qbit_torrent.save_path,
                        status_retry_count=0,
                        status_details=None
                    )
            elif downloads[0].status == TorrentDownloadStatus.FAILED_DOWNLOAD == download_status:
                await torrent_download_repo.update_downloads(
                    download_ids=[download.id for download in downloads],
                    status=download_status,
                    status_retry_count=downloads[0].status_retry_count + 1,
                    status_details=f"Torrent found in a failed state in qBit: {qbit_download.state}",
                )
            elif downloads[0].status != download_status:
                if download_status == TorrentDownloadStatus.FAILED_DOWNLOAD:
                    await torrent_download_repo.update_downloads(
                        download_ids=[download.id for download in downloads],
                        status=download_status,
                        status_retry_count=0,
                        status_details=f"Torrent found in a failed state in qBit: {qbit_download.state}"
                    )
                    statuses_to_audit.append(TorrentDownloadStatus.FAILED_DOWNLOAD)
                else:
                    await torrent_download_repo.update_downloads(
                        download_ids=[download.id for download in downloads],
                        status=download_status,
                        status_retry_count=0,
                        status_details=None
                    )

            await self._audit_log_torrent_processing_action(download_status=download_status,
                                                            torrent_download=downloads[0],
                                                            db_torrents=[download.torrent for download in downloads],
                                                            only_audit_statuses=statuses_to_audit)

    async def advance_downloads_in_downloading_status(self):
        torrent_download_repo = TorrentDownloadRepo(get_session())
        downloads = await torrent_download_repo.get_downloads(
            statuses=[TorrentDownloadStatus.DOWNLOADING],
            load_relations=True
        )
        downloads = await self._filter_out_and_update_superseded_downloads(downloads=downloads)
        if not downloads:
            return

        hash_downloads_map: dict[str, list[TorrentDownload]] = defaultdict(list)
        for download in downloads:
            hash_downloads_map[download.torrent.magnet_hash].append(download)
        qbit_downloads = await self._qbit_component.get_torrents(magnet_hashes=hash_downloads_map.keys())
        hash_qbit_download_map = {
            qbit_download.hash: qbit_download for qbit_download in qbit_downloads
        }

        for hash_, downloads in hash_downloads_map.items():
            statuses_to_audit = [TorrentDownloadStatus.DELETED, TorrentDownloadStatus.DISCARDED,
                                 TorrentDownloadStatus.DOWNLOADED, TorrentDownloadStatus.FAILED_DOWNLOAD]
            qbit_download = hash_qbit_download_map.get(hash_)
            download_status = self._resolve_torrent_download_qbit_status(qbit_download=qbit_download,
                                                                         current_status=downloads[0].status)
            if downloads[0].status != download_status:
                if download_status == TorrentDownloadStatus.FAILED_DOWNLOAD:
                    await torrent_download_repo.update_downloads(
                        download_ids=[download.id for download in downloads],
                        status=download_status,
                        status_retry_count=0,
                        status_details=f"Torrent found in a failed state in qBit: {qbit_download.state}"
                    )
                else:
                    await torrent_download_repo.update_downloads(
                        download_ids=[download.id for download in downloads],
                        status=download_status,
                        status_retry_count=0,
                        status_details=None
                    )

            await self._audit_log_torrent_processing_action(download_status=download_status,
                                                            torrent_download=downloads[0],
                                                            db_torrents=[download.torrent for download in downloads],
                                                            only_audit_statuses=statuses_to_audit)

    async def advance_downloads_in_downloaded_status(self) -> list[Coroutine]:
        torrent_download_repo = TorrentDownloadRepo(get_session())
        downloads = await torrent_download_repo.get_downloads(
            statuses=[TorrentDownloadStatus.DOWNLOADED],
            load_relations=True
        )
        downloads.extend(await torrent_download_repo.get_downloads(
            statuses=[TorrentDownloadStatus.FAILED_PROCESSING],
            retry_count_less_than=DOWNLOAD_PROCESSING_RETRY_LIMIT,
            updated_at_before=datetime.now(UTC) - timedelta(minutes=5),
            load_relations=True
        ))
        downloads = await self._filter_out_and_update_superseded_downloads(downloads=downloads)
        if not downloads:
            return []

        hash_downloads_map: dict[str, list[TorrentDownload]] = defaultdict(list)
        for download in downloads:
            hash_downloads_map[download.torrent.magnet_hash].append(download)
        qbit_downloads = await self._qbit_component.get_torrents(magnet_hashes=hash_downloads_map.keys())
        hash_qbit_download_map = {qbit_download.hash: qbit_download for qbit_download in qbit_downloads}

        processing_tasks = []
        for hash_, downloads in hash_downloads_map.items():
            statuses_to_audit = [TorrentDownloadStatus.DELETED, TorrentDownloadStatus.DISCARDED,
                                 TorrentDownloadStatus.PROCESSING, TorrentDownloadStatus.FAILED_DOWNLOAD]
            qbit_download = hash_qbit_download_map.get(hash_)
            download_status = self._resolve_torrent_download_qbit_status(qbit_download=qbit_download,
                                                                         current_status=downloads[0].status)
            if downloads[0].status != download_status:
                if download_status == TorrentDownloadStatus.FAILED_DOWNLOAD:
                    await torrent_download_repo.update_downloads(
                        download_ids=[download.id for download in downloads],
                        filter_by_statuses=[TorrentDownloadStatus.FAILED_PROCESSING, TorrentDownloadStatus.DOWNLOADED],
                        status=TorrentDownloadStatus.FAILED_DOWNLOAD,
                        status_retry_count=0,
                        status_details=f"Torrent found in a failed state in qBit: {qbit_download.state}"
                    )
                else:
                    status_retry_count = (downloads[0].status_retry_count + 1) \
                        if downloads[0].status == TorrentDownloadStatus.FAILED_PROCESSING else 0
                    await torrent_download_repo.update_downloads(
                        download_ids=[download.id for download in downloads],
                        filter_by_statuses=[TorrentDownloadStatus.FAILED_PROCESSING, TorrentDownloadStatus.DOWNLOADED],
                        status=download_status,
                        status_retry_count=status_retry_count,
                        status_details=None
                    )
            if download_status == TorrentDownloadStatus.DOWNLOADED:
                try:
                    destination_path, source_file_path, processing_task = \
                        await self._processing_component.initiate_download_processing(
                            torrent_downloads=downloads, qbit_torrent=qbit_download
                        )
                except Exception as e:
                    status_retry_count = (downloads[0].status_retry_count + 1) \
                        if downloads[0].status == TorrentDownloadStatus.FAILED_PROCESSING else 0
                    await torrent_download_repo.update_downloads(
                        download_ids=[download.id for download in downloads],
                        filter_by_statuses=[TorrentDownloadStatus.FAILED_PROCESSING, TorrentDownloadStatus.DOWNLOADED],
                        status=TorrentDownloadStatus.FAILED_PROCESSING,
                        status_retry_count=status_retry_count,
                        status_details=f"Error while processing torrent download: {e}"
                    )
                    download_status = TorrentDownloadStatus.FAILED_PROCESSING
                    statuses_to_audit.append(TorrentDownloadStatus.FAILED_PROCESSING)
                    if isinstance(e, TVDBIncompleteDataException):
                        self.logger.debug(f"Error while processing torrent download: {e}")
                    else:
                        self.logger.warning(f"Error while processing torrent download: {e}", exc_info=True)
                else:
                    await torrent_download_repo.update_downloads(
                        download_ids=[download.id for download in downloads],
                        filter_by_statuses=[TorrentDownloadStatus.FAILED_PROCESSING, TorrentDownloadStatus.DOWNLOADED],
                        status=TorrentDownloadStatus.PROCESSING,
                        status_retry_count=0,
                        status_details=None,
                        source_path=str(source_file_path),
                        destination_path=str(destination_path)
                    )
                    processing_tasks.append(processing_task)
                    download_status = TorrentDownloadStatus.PROCESSING

            await self._audit_log_torrent_processing_action(download_status=download_status,
                                                            torrent_download=downloads[0],
                                                            db_torrents=[download.torrent for download in downloads],
                                                            only_audit_statuses=statuses_to_audit)

        return processing_tasks

    @staticmethod
    def _resolve_torrent_download_qbit_status(qbit_download: QBitTorrent | None,
                                              current_status: TorrentDownloadStatus) -> TorrentDownloadStatus:
        if not qbit_download:
            if current_status in [TorrentDownloadStatus.FAILED_DOWNLOAD_INIT,
                                  TorrentDownloadStatus.PENDING]:
                return current_status
            else:
                return TorrentDownloadStatus.DELETED
        elif qbit_download.state in QBITTORRENT_ERROR_STATES:
            return TorrentDownloadStatus.FAILED_DOWNLOAD
        elif qbit_download.state in QBITTORRENT_UNFINISHED_STATES or qbit_download.progress < 1:
            return TorrentDownloadStatus.DOWNLOADING
        elif qbit_download.progress == 1:
            return TorrentDownloadStatus.DOWNLOADED
        else:
            raise

    @staticmethod
    async def get_torrent_tags_and_category(torrent: Torrent) -> tuple[list[str], str | None]:
        torrent_tags = []
        if config.user_settings.apply_anime_title_as_torrent_tag:
            torrent_tags.append(torrent.tracked_anime_episode.tracked_anime.preferred_title)
        if config.user_settings.apply_release_group_as_torrent_tag:
            torrent_tags.append(torrent.release_group)
        if config.user_settings.apply_encoding_as_torrent_tag and torrent.encoding:
            torrent_tags.append(torrent.encoding.value)
        if config.user_settings.apply_resolution_as_torrent_tag and torrent.resolution:
            torrent_tags.append(torrent.resolution.value)
        if config.user_settings.apply_language_code_as_torrent_tag and torrent.language_code:
            torrent_tags.append(torrent.language_code)
        category = config.user_settings.torrent_category or None
        return torrent_tags, category

    @staticmethod
    async def _filter_out_and_update_superseded_downloads(downloads: list[TorrentDownload]) -> list[TorrentDownload]:
        torrent_download_repo = TorrentDownloadRepo(get_session())
        superseded_downloads = []
        remaining_downloads = []
        for download in downloads:
            if not download.torrent.override \
                    and (await torrent_download_repo.get_active_downloads_by_episode_id_and_part(
                        tracked_anime_episode_id=download.torrent.tracked_anime_episode_id,
                        episode_part=download.torrent.episode_part,
                        episode_part_ceiling=download.torrent.episode_part_ceiling,
                        exclude_download_ids=[download.id],
                        created_at_after=download.created_at,
                        created_at_tiebreak_id=download.id,
                        only=('id',)
                    )):
                superseded_downloads.append(download)
            else:
                remaining_downloads.append(download)
        await torrent_download_repo.update_downloads(
            download_ids=[superseded_download.id for superseded_download in superseded_downloads],
            status=TorrentDownloadStatus.DISCARDED,
            status_retry_count=0,
            status_details=f"Superseded by a newer download"
        )
        return remaining_downloads

    async def mark_stuck_downloads_as_failed(self):
        torrent_download_repo = TorrentDownloadRepo(get_session())
        downloading_downloads = await torrent_download_repo.get_downloads(
            statuses=[TorrentDownloadStatus.DOWNLOADING],
            updated_at_before=datetime.now(UTC) - timedelta(
                minutes=config.user_settings.set_download_as_failed_after_minutes
            ),
            load_relations=True
        )
        await torrent_download_repo.update_downloads(
            download_ids=[download.id for download in downloading_downloads],
            status=TorrentDownloadStatus.FAILED_DOWNLOAD,
            status_retry_count=0,
            status_details=f"Download set to failed due to being in the downloading state for "
                           f"{get_human_readable_time(
                               config.user_settings.set_download_as_failed_after_minutes * 60
                           )}"
        )

        hash_downloads_map = defaultdict(list)
        for download in downloading_downloads:
            hash_downloads_map[download.torrent.magnet_hash].append(download)
        for hash_, downloads in hash_downloads_map.items():
            await self._audit_log_torrent_processing_action(
                download_status=TorrentDownloadStatus.FAILED_DOWNLOAD,
                torrent_download=downloads[0],
                db_torrents=[download.torrent for download in downloads],
            )

        processing_downloads = await torrent_download_repo.get_downloads(
            statuses=[TorrentDownloadStatus.PROCESSING],
            updated_at_before=datetime.now(UTC) - timedelta(
                minutes=config.user_settings.set_processing_as_failed_after_minutes
            ),
            load_relations=True
        )
        await torrent_download_repo.update_downloads(
            download_ids=[download.id for download in processing_downloads],
            status=TorrentDownloadStatus.FAILED_PROCESSING,
            status_retry_count=0,
            status_details=f"Download set to failed due to being in the processing state for "
                           f"{get_human_readable_time(
                               config.user_settings.set_processing_as_failed_after_minutes * 60
                           )}"
        )

        hash_downloads_map = defaultdict(list)
        for download in processing_downloads:
            hash_downloads_map[download.torrent.magnet_hash].append(download)
        for hash_, downloads in hash_downloads_map.items():
            await self._audit_log_torrent_processing_action(
                download_status=TorrentDownloadStatus.FAILED_PROCESSING,
                torrent_download=downloads[0],
                db_torrents=[download.torrent for download in downloads],
            )

    async def _audit_log_torrent_processing_action(self,
                                                   download_status: TorrentDownloadStatus,
                                                   torrent_download: TorrentDownload,
                                                   db_torrents: list[Torrent],
                                                   only_audit_statuses: list[TorrentDownloadStatus] | None = None,):
        if only_audit_statuses is not None and download_status not in only_audit_statuses:
            return
        status_code_map = {
            TorrentDownloadStatus.DOWNLOADING: AuditLogCode.TORRENT_DOWNLOAD_STARTED,
            TorrentDownloadStatus.DOWNLOADED: AuditLogCode.TORRENT_DOWNLOAD_FINISHED,
            TorrentDownloadStatus.FAILED_DOWNLOAD: AuditLogCode.TORRENT_DOWNLOAD_FAILED,
            TorrentDownloadStatus.FAILED_DOWNLOAD_INIT: AuditLogCode.TORRENT_DOWNLOAD_FAILED,
            TorrentDownloadStatus.DISCARDED: AuditLogCode.TORRENT_DOWNLOAD_DISCARDED,
            TorrentDownloadStatus.DELETED: AuditLogCode.TORRENT_DOWNLOAD_DELETED,
            TorrentDownloadStatus.PROCESSING: AuditLogCode.TORRENT_PROCESSING_STARTED,
            TorrentDownloadStatus.FAILED_PROCESSING: AuditLogCode.TORRENT_PROCESSING_FAILED,
        }
        await self._audit_log_component.log_torrent_processing_action(
            code=status_code_map[download_status],
            torrent_download=torrent_download,
            db_torrents=db_torrents
        )
        global_status.tracked_anime_updated()

    # noinspection PyMethodMayBeStatic
    async def get_magnet_hash_latest_effective_download_time_map(self,
                                                                 db_torrents: list[Torrent]) -> dict[str, datetime]:
        db_torrents_spaces = set((db_torrent.tracked_anime_episode_id,
                                  db_torrent.episode_part,
                                  db_torrent.episode_part_ceiling) for db_torrent in db_torrents)
        space_latest_copied_to_destination_path_at_rows = await TorrentDownloadRepo(
            get_session()
        ).get_latest_copied_to_destination_path_at_by_torrent_space(torrent_spaces=db_torrents_spaces)
        space_copied_to_destination_path_at_map = {
            (tracked_anime_episode_id, episode_part, episode_part_ceiling): copied_to_destination_path_at
            for tracked_anime_episode_id, episode_part, episode_part_ceiling, copied_to_destination_path_at
            in space_latest_copied_to_destination_path_at_rows
        }
        magnet_hash_latest_effective_download_time_map = {}
        for db_torrent in db_torrents:
            space = (db_torrent.tracked_anime_episode_id, db_torrent.episode_part, db_torrent.episode_part_ceiling)
            latest_copied_to_destination_path_at = space_copied_to_destination_path_at_map.get(space)
            if latest_copied_to_destination_path_at is None:
                continue
            existing_latest = magnet_hash_latest_effective_download_time_map.get(db_torrent.magnet_hash)
            if existing_latest is None or latest_copied_to_destination_path_at > existing_latest:
                magnet_hash_latest_effective_download_time_map[db_torrent.magnet_hash] = \
                    latest_copied_to_destination_path_at

        return magnet_hash_latest_effective_download_time_map
