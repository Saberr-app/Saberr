from collections import defaultdict
from datetime import timedelta, datetime

from app_state import worker_manager
from common.db import get_session
from common.decorators import api_component, require_db_session
from common.exceptions import ExternalServiceException, InvalidReleaseGroupException, ValidationException, \
    NotFoundException
from components import BaseComponent
from components.operational_components.torrent_download_component import TorrentDownloadComponent
from components.service_components.rss_component import RSSComponent
from components.service_components.qbit_component import QBitComponent
from components.operational_components.torrent_component import TorrentComponent
from components.operational_components.tracked_anime_component import TrackedAnimeComponent
from components.service_components.anilist_component import AnilistComponent
from components.operational_components.tracked_anime_episode_component import TrackedAnimeEpisodeComponent
from api.schemas.torrent_schemas import (
    TorrentSearchRequest, TorrentDiscardRequest, TorrentDownloadRequest,
    TorrentListResponse, TorrentPullStatus, TorrentListItem, TorrentDownloadResponse, TorrentOverrideRequest,
    TorrentOverrideResponse,
)
from config import config
from constants import WorkerName, TorrentDownloadStatus
from dto.anilist import AnilistAnime
from dto.nyaa_item import RawTorrent, NyaaItem
from dto.orm_models import Torrent, TrackedAnime
from dto.qbit import QBitTorrent
from repositories.tracked_anime_repositories.tracked_anime_episode_repo import TrackedAnimeEpisodeRepo
from system import UNSET
from repositories.torrent_repositories.torrent_download_repo import TorrentDownloadRepo
from repositories.torrent_repositories.torrent_repo import TorrentRepo
from utils.helpers.fuzzy_matcher import fuzzy_match_title_parts


class TorrentAPIComponent(BaseComponent):

    def __init__(self):
        super().__init__()
        self._rss_component = RSSComponent()
        self._torrent_component = TorrentComponent()
        self._torrent_download_component = TorrentDownloadComponent()
        self._qbit_component = QBitComponent()
        self._tracked_anime_component = TrackedAnimeComponent()
        self._anilist_component = AnilistComponent()
        self._tracked_anime_episode_component = TrackedAnimeEpisodeComponent()

    @api_component
    async def get_torrents(self, raw_torrents: list[RawTorrent] | None = None) -> TorrentListResponse:
        if raw_torrents is None:
            raw_torrents = await self._rss_component.get_latest_raw_torrents()
        magnet_hash_raw_torrent_map = {raw_torrent.nyaa_item.magnet_hash: raw_torrent for raw_torrent in raw_torrents}
        db_torrents = await self._torrent_component.get_torrents_by_hashes(
            magnet_hashes=magnet_hash_raw_torrent_map.keys()
        )
        magnet_hash_db_torrents_group_map = defaultdict(list)
        for db_torrent in db_torrents:
            magnet_hash_db_torrents_group_map[db_torrent.magnet_hash].append(db_torrent)
        magnet_hash_latest_effective_download_time_map = await \
            self._torrent_download_component.get_magnet_hash_latest_effective_download_time_map(db_torrents=db_torrents)
        try:
            qbit_torrents = await self._qbit_component.get_torrents(
                magnet_hashes=magnet_hash_db_torrents_group_map.keys()
            )
        except ExternalServiceException as e:
            self.logger.warning(f"Failed to get torrents from qBittorrent: {e}")
            qbit_torrents = []
        magnet_hash_qbit_torrent_map = {qbit_torrent.hash: qbit_torrent for qbit_torrent in qbit_torrents}
        magnet_hash_anime_map = await self._get_magnet_hash_anime_map(
            raw_torrents=raw_torrents,  magnet_hash_db_torrents_group_map=magnet_hash_db_torrents_group_map
        )
        tracked_anime = await self._tracked_anime_component.get_tracked_anime_by_anilist_ids(
            anilist_ids=[raw_torrent.anilist_anime_min.id for raw_torrent in raw_torrents
                         if raw_torrent.anilist_anime_min]
        )
        tracked_anime_anilist_id_to_tracked_anime_map = {tracked_anime.anilist_id: tracked_anime
                                                         for tracked_anime in tracked_anime}
        torrent_items = [
            self._to_torrent_item(
                raw_torrent=raw_torrent,
                qbit_torrent=magnet_hash_qbit_torrent_map.get(raw_torrent.nyaa_item.magnet_hash),
                db_torrents=magnet_hash_db_torrents_group_map.get(raw_torrent.nyaa_item.magnet_hash) or [],
                anilist_anime=magnet_hash_anime_map.get(raw_torrent.nyaa_item.magnet_hash),
                tracked_anime=tracked_anime_anilist_id_to_tracked_anime_map.get(raw_torrent.anilist_anime_min.id)
                if raw_torrent.anilist_anime_min else None,
                latest_effective_download_time_for_episode_space=magnet_hash_latest_effective_download_time_map.get(
                    raw_torrent.nyaa_item.magnet_hash
                )
            )
            for raw_torrent in raw_torrents
        ]
        return TorrentListResponse(
            torrents=torrent_items,
            pull_status=await self.get_torrents_pull_status()
        )

    @require_db_session
    @api_component
    async def get_torrents_pull_status(self, ref: int = 1) -> TorrentPullStatus:
        worker_details = worker_manager.get_worker_details(worker_id=WorkerName.CONSUME_RSS_FEEDS.name)
        last_pull = worker_details.last_run.last_run_time if worker_details and worker_details.last_run else None
        next_pull = worker_manager.get_worker_next_run(worker_id=WorkerName.CONSUME_RSS_FEEDS.name)
        return TorrentPullStatus(
            ref=ref,
            currently_pulling=self._rss_component.rss_locked(),
            last_pull=last_pull,
            next_pull=next_pull,
        )

    @api_component
    async def search_torrents(self, body: TorrentSearchRequest) -> TorrentListResponse:
        if body.release_groups is not None:
            if invalid_releases_groups := (set(body.release_groups) - config.release_groups_map.keys()):
                raise InvalidReleaseGroupException(f"Invalid release groups: {', '.join(invalid_releases_groups)}.")
            release_groups = body.release_groups
        else:
            release_groups = list(config.release_groups_map)
        raw_torrents = await self._rss_component.get_torrents(query=body.query,
                                                              release_groups=release_groups)
        return await self.get_torrents(raw_torrents=raw_torrents)

    @api_component
    async def discard_torrents(self, body: TorrentDiscardRequest) -> None:
        db_torrents = await self._torrent_component.get_torrents_by_hashes(magnet_hashes=body.magnet_hashes)
        download_ids_to_discard = set()
        for db_torrent in db_torrents:
            if db_torrent.effective_download:
                if db_torrent.effective_download.status == TorrentDownloadStatus.PROCESSED:
                    raise ValidationException(f"Cannot discard an already processed torrent:"
                                              f" {db_torrent.magnet_hash}.")
                download_ids_to_discard.add(db_torrent.effective_download.id)
        await TorrentRepo(get_session()).update_torrents_by_magnet_hashes(
            magnet_hashes=body.magnet_hashes,
            discarded=True
        )
        if download_ids_to_discard:
            await TorrentDownloadRepo(get_session()).update_downloads(download_ids=download_ids_to_discard,
                                                                      status=TorrentDownloadStatus.DISCARDED)

    @api_component
    async def download_torrent(self, body: TorrentDownloadRequest) -> TorrentDownloadResponse:
        if (body.episode_part or body.episode_part_ceiling) and len(body.episode_numbers) > 1:
            raise ValidationException("Cannot specify episode part and episode part ceiling for multiple episodes.")
        if not body.episode_numbers or any(episode_number <= 0 for episode_number in body.episode_numbers):
            raise ValidationException("Episode numbers must be greater than 0.")
        tracked_anime = await self._tracked_anime_component.get_tracked_anime_by_id(
            tracked_anime_id=body.tracked_anime_id
        )
        if not tracked_anime:
            raise NotFoundException(f"Tracked anime {body.tracked_anime_id} not found.")
        try:
            nyaa_item = NyaaItem.from_xml_string(xml_data=body.rss_xml)
        except Exception as e:
            raise ValidationException(f"Invalid RSS XML: {e}")
        db_torrents = await self._torrent_component.get_torrents_by_hashes(magnet_hashes=[body.magnet_hash])
        if db_torrents:
            parent_db_torrent = [db_torrent for db_torrent in db_torrents if not db_torrent.parent_torrent_id][0]
            mark_for_deletion = False
            if parent_db_torrent.effective_download:
                if parent_db_torrent.effective_download.status in [TorrentDownloadStatus.DELETED,
                                                                   TorrentDownloadStatus.DISCARDED]:
                    mark_for_deletion = True  # start clean
                else:
                    raise ValidationException("Torrent already downloaded. If it needs to be re-downloaded, "
                                              "delete the original download first.")
            episode_numbers = [db_torrent.tracked_anime_episode.episode_number for db_torrent in db_torrents]
            episode_part = db_torrents[0].episode_part
            episode_part_ceiling = db_torrents[0].episode_part_ceiling
            tracked_anime_id = db_torrents[0].tracked_anime_episode.tracked_anime_id
            if (mark_for_deletion
                    or set(episode_numbers) != set(body.episode_numbers)
                    or episode_part != body.episode_part
                    or episode_part_ceiling != body.episode_part_ceiling
                    or tracked_anime_id != body.tracked_anime_id):
                await TorrentRepo(get_session()).delete_torrents(torrent_ids=[db_torrent.id for db_torrent
                                                                              in db_torrents])
                db_torrents = []
            else:
                for db_torrent in db_torrents:
                    await TorrentRepo(get_session()).update_torrent(
                        torrent_id=db_torrent.id,
                        release_group=body.release_group,
                        title=tracked_anime.romaji_title,
                        language_code=body.language_code,
                        encoding=body.encoding,
                        resolution=body.resolution,
                        version_number=body.version,
                        repack_indicator=body.is_repack,
                        source=body.source,
                        discarded=False,
                        override=body.discard_future_torrents
                    )
                    await self._tracked_anime_episode_component.get_or_create_tracked_anime_episode(
                        tracked_anime=tracked_anime,
                        episode_number=db_torrent.tracked_anime_episode.episode_number,
                        tvdb_data_freshness_minimum=timedelta(hours=12),
                        set_auto_discard_to=body.discard_future_torrents or UNSET
                    )
        if not db_torrents:
            episode_numbers = sorted(body.episode_numbers)
            tracked_anime_episode = await self._tracked_anime_episode_component.get_or_create_tracked_anime_episode(
                tracked_anime=tracked_anime,
                episode_number=episode_numbers[0],
                tvdb_data_freshness_minimum=timedelta(hours=12),
                set_auto_discard_to=body.discard_future_torrents
            )
            shared_db_torrent_attributes = {
                "magnet_hash": nyaa_item.magnet_hash,
                "rss_xml": nyaa_item.source_xml,
                "torrent_link": nyaa_item.link,
                "torrent_title": nyaa_item.title,
                "release_group": body.release_group,
                "title": tracked_anime.romaji_title,
                "language_code": body.language_code,
                "encoding": body.encoding,
                "resolution": body.resolution,
                "version_number": body.version,
                "repack_indicator": body.is_repack,
                "source": body.source,
                "discarded": False,
                "override": body.discard_future_torrents
            }
            parent_db_torrent = await TorrentRepo(get_session()).create_torrent(
                tracked_anime_episode_id=tracked_anime_episode.id,
                episode_number=episode_numbers[0],
                episode_part=body.episode_part,
                episode_part_ceiling=body.episode_part_ceiling,
                parent_torrent_id=None,
                **shared_db_torrent_attributes
            )
            db_torrents = [parent_db_torrent]
            for episode_number in episode_numbers[1:]:
                tracked_anime_episode = await self._tracked_anime_episode_component.get_or_create_tracked_anime_episode(
                    tracked_anime=tracked_anime,
                    episode_number=episode_number,
                    tvdb_data_freshness_minimum=timedelta(hours=12),
                    set_auto_discard_to=body.discard_future_torrents
                )
                db_torrent = await TorrentRepo(get_session()).create_torrent(
                    tracked_anime_episode_id=tracked_anime_episode.id,
                    episode_number=episode_number,
                    episode_part=0,
                    episode_part_ceiling=0,
                    parent_torrent_id=parent_db_torrent.id,
                    **shared_db_torrent_attributes
                )
                db_torrents.append(db_torrent)

        parent_torrent_id, children_torrent_ids = None, []
        for db_torrent in db_torrents:
            if not db_torrent.parent_torrent_id:
                parent_torrent_id = db_torrent.id
            else:
                children_torrent_ids.append(db_torrent.id)

        if body.release_group_override_settings is not None:
            if body.release_group not in config.release_groups_map:
                raise ValidationException(f"Invalid release group: {body.release_group}.")
            await self._tracked_anime_component.update_tracked_anime_release_group_overriding_title(
                tracked_anime_id=body.tracked_anime_id,
                release_group=body.release_group,
                title=body.release_group_override_settings.override_match_against,
                offset=body.release_group_override_settings.episode_number_offset
            )

        await get_session().commit()  # safe to commit so far (identification)
        download = await self._torrent_component.select_torrent_for_downloading(magnet_hash=nyaa_item.magnet_hash)

        parent_db_torrent = await TorrentRepo(get_session()).get_torrent(torrent_id=parent_torrent_id,
                                                                         load_relations=True)
        tracked_anime = await self._tracked_anime_component.get_tracked_anime_by_id(
            tracked_anime_id=body.tracked_anime_id, load_relations=False
        )
        try:
            qbit_torrent = await self._qbit_component.get_torrent(magnet_hash=nyaa_item.magnet_hash)
        except ExternalServiceException as e:
            self.logger.warning(f"Failed to get torrent from qBittorrent: {e}")
            qbit_torrent = None
        return TorrentDownloadResponse(
            download=TorrentListItem.Download(
                id=download.id,
                status=download.status,
                status_details=download.status_details,
                download_directory_path=download.download_directory_path,
                destination_path=download.destination_path,
                copied_to_destination_path_at=download.copied_to_destination_path_at,
                qbit_status=qbit_torrent.state if qbit_torrent else None,
                qbit_progress=qbit_torrent.progress if qbit_torrent else None,
                qbit_eta=qbit_torrent.eta if qbit_torrent else None,
            ),
            rss_torrent=TorrentDownloadResponse.RSSTorrent(
                title=nyaa_item.title,
                web_link=nyaa_item.web_link,
                seeders=nyaa_item.seeders,
                leechers=nyaa_item.leechers,
                downloads=nyaa_item.downloads,
                magnet_hash=nyaa_item.magnet_hash,
                category=nyaa_item.category,
                size=nyaa_item.size,
                description=nyaa_item.clean_description,
                created_at=nyaa_item.created_at,
                rss_xml=nyaa_item.source_xml,
                explicit_resolved_attributes=TorrentListItem.RSSTorrent.RSSTorrentResolvedAttributes(
                    release_group=parent_db_torrent.release_group,
                    title=parent_db_torrent.title,
                    episode_number=parent_db_torrent.episode_number,
                    version_number=parent_db_torrent.version_number,
                    language_code=parent_db_torrent.language_code,
                    repack_indicator=parent_db_torrent.repack_indicator,
                    resolution=parent_db_torrent.resolution,
                    source=parent_db_torrent.source,
                    encoding=parent_db_torrent.encoding,
                    censorship_status=None,
                    is_batch=False,
                    missing_required=False,
                )
            ),
            anilist_id=tracked_anime.anilist_id,
            anilist_english_title=tracked_anime.english_title,
            anilist_native_title=tracked_anime.native_title,
            anilist_romaji_title=tracked_anime.romaji_title,
            parent_id=parent_torrent_id,
            children_ids=children_torrent_ids,
            tracked_anime_id=tracked_anime.id,
            tracked_from_episode=tracked_anime.from_episode,
            anilist_episode_numbers=body.episode_numbers,
            anilist_episode_part=body.episode_part,
            anilist_episode_part_ceiling=body.episode_part_ceiling
        )

    async def override_torrent(self, torrent_id: int, body: TorrentOverrideRequest) -> TorrentOverrideResponse:
        torrent_repo = TorrentRepo(get_session())
        parent_torrent = await torrent_repo.get_torrent(torrent_id=torrent_id, load_relations=True)
        if not parent_torrent:
            raise NotFoundException(f"Torrent {torrent_id} not found.")
        if parent_torrent.parent_torrent_id:
            torrent_id = parent_torrent.parent_torrent_id
            parent_torrent = await torrent_repo.get_torrent(torrent_id=torrent_id, load_relations=True)
        other_torrents = await torrent_repo.get_torrents_by_parent_ids(parent_ids=[torrent_id], load_relations=True)
        if not parent_torrent.download:
            effective_download = await self._torrent_component.select_torrent_for_downloading(
                parent_torrent.magnet_hash
            )
        else:
            download_ids = {other_torrent.effective_download.id
                            for other_torrent in (other_torrents + [parent_torrent])}
            await TorrentDownloadRepo(get_session()).update_downloads(download_ids=download_ids,
                                                                      status=TorrentDownloadStatus.PENDING,
                                                                      status_details=None,
                                                                      status_retry_count=0,
                                                                      source_path=None,
                                                                      destination_path=None,
                                                                      copied_to_destination_path_at=None)
            effective_download = parent_torrent.effective_download
        await torrent_repo.bulk_update_torrents(data=[
            {
                "id": torrent.id,
                "discarded": False,
                "override": True,
            } for torrent in (other_torrents + [parent_torrent])
        ])
        if body.discard_future_torrents:
            tracked_anime_episode_ids = {torrent.tracked_anime_episode_id
                                         for torrent in (other_torrents + [parent_torrent])}
            await TrackedAnimeEpisodeRepo(get_session()).update_tracked_anime_episodes(
                tracked_anime_episode_ids=tracked_anime_episode_ids, auto_discard=True
            )
        return TorrentOverrideResponse(
            download_id=effective_download.id,
        )

    def _to_torrent_item(self,
                         raw_torrent: RawTorrent,
                         qbit_torrent: QBitTorrent | None,
                         db_torrents: list[Torrent],
                         anilist_anime: AnilistAnime,
                         tracked_anime: TrackedAnime,
                         latest_effective_download_time_for_episode_space: datetime | None) -> TorrentListItem:
        parent_db_torrent, other_db_torrents = None, []
        for db_torrent in db_torrents:
            if not db_torrent.parent_torrent_id:
                parent_db_torrent = db_torrent
            else:
                other_db_torrents.append(db_torrent)
        fuzzy_match = fuzzy_match_title_parts(release_title=raw_torrent.nyaa_item.title)
        fuzzy_resolved_attributes = TorrentListItem.RSSTorrent.RSSTorrentResolvedAttributes(
            release_group=fuzzy_match.release_group,
            title=fuzzy_match.search_title,
            episode_number=fuzzy_match.episode_number,
            version_number=fuzzy_match.version_number,
            language_code=fuzzy_match.language_code,
            repack_indicator=fuzzy_match.repack_indicator,
            resolution=fuzzy_match.resolution,
            source=fuzzy_match.source,
            encoding=fuzzy_match.encoding,
            censorship_status=fuzzy_match.censorship_status,
            is_batch=fuzzy_match.is_batch,
            missing_required=fuzzy_match.missing_required,
        )
        rss_torrent = TorrentListItem.RSSTorrent(
            title=raw_torrent.nyaa_item.title,
            web_link=raw_torrent.nyaa_item.web_link,
            seeders=raw_torrent.nyaa_item.seeders,
            leechers=raw_torrent.nyaa_item.leechers,
            downloads=raw_torrent.nyaa_item.downloads,
            magnet_hash=raw_torrent.nyaa_item.magnet_hash,
            category=raw_torrent.nyaa_item.category,
            size=raw_torrent.nyaa_item.size,
            description=raw_torrent.nyaa_item.clean_description,
            created_at=raw_torrent.nyaa_item.created_at,
            rss_xml=raw_torrent.nyaa_item.source_xml,
            explicit_resolved_attributes=self._to_resolved_attributes_from_torrent(raw_torrent=raw_torrent,
                                                                                   db_torrent=parent_db_torrent),
            fuzzy_resolved_attributes=fuzzy_resolved_attributes
        )
        download = TorrentListItem.Download(
            id=parent_db_torrent.effective_download.id,
            status=parent_db_torrent.effective_download.status,
            status_details=parent_db_torrent.effective_download.status_details,
            download_directory_path=parent_db_torrent.effective_download.download_directory_path,
            destination_path=parent_db_torrent.effective_download.destination_path,
            copied_to_destination_path_at=parent_db_torrent.effective_download.copied_to_destination_path_at,
            qbit_status=qbit_torrent.state if qbit_torrent else None,
            qbit_progress=qbit_torrent.progress if qbit_torrent else None,
            qbit_eta=qbit_torrent.eta if qbit_torrent else None,
        ) if parent_db_torrent and parent_db_torrent.effective_download else None
        notes = [TorrentListItem.Note(text=note[0], is_error=note[1]) for note in raw_torrent.notes]

        if db_torrents:
            episode_numbers = sorted([db_torrent.tracked_anime_episode.episode_number for db_torrent in db_torrents])
            episode_part = parent_db_torrent.episode_part if parent_db_torrent else None
            episode_part_ceiling = parent_db_torrent.episode_part_ceiling if parent_db_torrent else None
        else:
            episode_numbers = [raw_torrent.anilist_episode_number] if raw_torrent.anilist_episode_number else []
            episode_part = raw_torrent.episode_part
            episode_part_ceiling = raw_torrent.episode_part_ceiling

        if parent_db_torrent:
            tracked_anime = parent_db_torrent.tracked_anime_episode.tracked_anime
        if tracked_anime:
            tracked_anime_id = tracked_anime.id
        else:
            tracked_anime_id = None

        superseded = raw_torrent.superseded
        if parent_db_torrent \
                and parent_db_torrent.effective_download \
                and latest_effective_download_time_for_episode_space:
            if parent_db_torrent.effective_download.copied_to_destination_path_at \
                    and parent_db_torrent.effective_download.copied_to_destination_path_at \
                    < latest_effective_download_time_for_episode_space:
                superseded = True

        return TorrentListItem(
            rss_torrent=rss_torrent,
            download=download,
            notes=notes,
            anilist_id=anilist_anime.id if anilist_anime else None,
            anilist_english_title=anilist_anime.english_title if anilist_anime else None,
            anilist_native_title=anilist_anime.native_title if anilist_anime else None,
            anilist_romaji_title=anilist_anime.romaji_title if anilist_anime else None,
            parent_id=parent_db_torrent.id if parent_db_torrent else None,
            children_ids=[db_torrent.id for db_torrent in other_db_torrents],
            tracked_anime_id=tracked_anime_id,
            tracked_from_episode=tracked_anime.from_episode if tracked_anime else None,
            anilist_episode_numbers=episode_numbers,
            anilist_episode_part=episode_part,
            anilist_episode_part_ceiling=episode_part_ceiling,
            selected=raw_torrent.selected,
            superseded=superseded,
            discarded=raw_torrent.discarded,
            profile_shortcomings=raw_torrent.profile_shortcomings
        )

    # noinspection PyMethodMayBeStatic
    def _to_resolved_attributes_from_torrent(
            self,
            raw_torrent: RawTorrent,
            db_torrent: Torrent | None = None
    ) -> TorrentListItem.RSSTorrent.RSSTorrentResolvedAttributes:
        if db_torrent:
            return TorrentListItem.RSSTorrent.RSSTorrentResolvedAttributes(
                release_group=db_torrent.release_group,
                title=db_torrent.title,
                episode_number=db_torrent.episode_number,
                version_number=db_torrent.version_number,
                language_code=db_torrent.language_code,
                repack_indicator=db_torrent.repack_indicator,
                resolution=db_torrent.resolution,
                source=db_torrent.source,
                encoding=db_torrent.encoding,
                censorship_status=raw_torrent.title_parts.censorship_status if raw_torrent.title_parts else None,
                is_batch=False,
                missing_required=False,
            )
        else:
            return TorrentListItem.RSSTorrent.RSSTorrentResolvedAttributes(
                    release_group=raw_torrent.title_parts.release_group,
                    title=raw_torrent.title_parts.search_title,
                    episode_number=raw_torrent.title_parts.episode_number,
                    version_number=raw_torrent.title_parts.version_number,
                    language_code=raw_torrent.title_parts.language_code,
                    repack_indicator=raw_torrent.title_parts.repack_indicator,
                    resolution=raw_torrent.title_parts.resolution,
                    source=raw_torrent.title_parts.source,
                    encoding=raw_torrent.title_parts.encoding,
                    censorship_status=raw_torrent.title_parts.censorship_status,
                    is_batch=raw_torrent.title_parts.is_batch,
                    missing_required=raw_torrent.title_parts.missing_required,
                ) if raw_torrent.title_parts else None

    async def _get_magnet_hash_anime_map(self,
                                         raw_torrents: list[RawTorrent],
                                         magnet_hash_db_torrents_group_map: dict[str, list[Torrent]]):
        magnet_hash_anilist_id_map = {}
        for raw_torrent in raw_torrents:
            if magnet_hash_db_torrents_group_map.get(raw_torrent.nyaa_item.magnet_hash):
                anilist_id = magnet_hash_db_torrents_group_map[raw_torrent.nyaa_item.magnet_hash][0] \
                    .tracked_anime_episode.tracked_anime.anilist_id
            else:
                anilist_id = raw_torrent.anilist_anime_min.id if raw_torrent.anilist_anime_min else None
            magnet_hash_anilist_id_map[raw_torrent.nyaa_item.magnet_hash] = anilist_id
        anime_list = await self._anilist_component.get_anime_records(
            anilist_anime_ids={anilist_id for anilist_id in magnet_hash_anilist_id_map.values() if anilist_id}
        )
        anilist_id_anime_map = {anime.id: anime for anime in anime_list}
        return {
            magnet_hash: anilist_id_anime_map.get(anime_id)
            for magnet_hash, anime_id in magnet_hash_anilist_id_map.items()
        }
