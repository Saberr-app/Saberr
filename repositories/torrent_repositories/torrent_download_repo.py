from datetime import datetime
from typing import Iterable

from sqlalchemy import select, update, delete, tuple_, func, ColumnOperators
from sqlalchemy.orm import contains_eager, joinedload, load_only

from constants import TorrentDownloadStatus
from dto.orm_models import TorrentDownload, Torrent, TrackedAnimeEpisode, TrackedAnime
from repositories import BaseRepo


class TorrentDownloadRepo(BaseRepo):

    # noinspection PyTypeChecker
    async def create_download(self,
                              torrent_id: int,
                              status: TorrentDownloadStatus,
                              status_retry_count: int,
                              status_details: str | None,
                              download_directory_path: str,
                              destination_path: str | None,
                              copied_to_destination_path_at: datetime | None) -> TorrentDownload:
        download = TorrentDownload(
            torrent_id=torrent_id,
            status=status,
            status_retry_count=status_retry_count,
            status_details=status_details,
            download_directory_path=download_directory_path,
            destination_path=destination_path,
            copied_to_destination_path_at=copied_to_destination_path_at  # noqa
        )
        self._session.add(download)
        await self._session.flush()
        return download

    async def get_download(self, download_id: int | None = None,
                           torrent_id: int | None = None,
                           load_relations: bool = False) -> TorrentDownload | None:
        if not any([download_id, torrent_id]):
            raise ValueError("At least one identifier must be provided.")
        query = select(TorrentDownload)
        if download_id:
            query = query.where(TorrentDownload.id == download_id)
        if torrent_id:
            query = query.where(TorrentDownload.torrent_id == torrent_id)
        if load_relations:
            query = query.options(joinedload(TorrentDownload.torrent)
                                  .joinedload(Torrent.tracked_anime_episode)
                                  .joinedload(TrackedAnimeEpisode.tracked_anime)
                                  .joinedload(TrackedAnime.profile))
        return (await self._session.execute(query)).unique().scalar_one_or_none()

    async def get_downloads_by_hashes(self, magnet_hashes: Iterable[str],
                                      load_relations: bool = False) -> list[TorrentDownload]:
        query = select(TorrentDownload).join(Torrent).where(Torrent.magnet_hash.in_(magnet_hashes))
        if load_relations:
            query = query.options(contains_eager(TorrentDownload.torrent)
                                  .joinedload(Torrent.tracked_anime_episode)
                                  .joinedload(TrackedAnimeEpisode.tracked_anime)
                                  .joinedload(TrackedAnime.profile))
        return (await self._session.execute(query)).scalars().all()

    async def get_downloads(self,
                            download_ids: list[int] | None = None,
                            torrent_ids: list[str] | None = None,
                            statuses: list[TorrentDownloadStatus] | None = None,
                            retry_count_less_than: int | None = None,
                            retry_count_minimum: int | None = None,
                            created_at_after: datetime | None = None,
                            updated_at_before: datetime | None = None,
                            load_relations: bool = False,
                            sort_by: ColumnOperators | None = None,
                            offset: int | None = None,
                            limit: int | None = None) -> list[TorrentDownload]:
        query = select(TorrentDownload)
        if download_ids:
            query = query.where(TorrentDownload.id.in_(download_ids))
        if torrent_ids:
            query = query.where(TorrentDownload.torrent_id.in_(torrent_ids))
        if statuses:
            query = query.where(TorrentDownload.status.in_(statuses))
        if retry_count_less_than:
            query = query.where(TorrentDownload.status_retry_count < retry_count_less_than)
        if retry_count_minimum:
            query = query.where(TorrentDownload.status_retry_count >= retry_count_minimum)
        if created_at_after:
            query = query.where(TorrentDownload.created_at > created_at_after)
        if updated_at_before:
            query = query.where(TorrentDownload.updated_at < updated_at_before)
        if sort_by is not None:
            query = query.order_by(sort_by)
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        if load_relations:
            query = query.options(joinedload(TorrentDownload.torrent)
                                  .joinedload(Torrent.tracked_anime_episode)
                                  .joinedload(TrackedAnimeEpisode.tracked_anime)
                                  .joinedload(TrackedAnime.processing_settings))
        return (await self._session.execute(query)).scalars().all()

    async def update_download(self, download_id: int, **update_data):
        if not update_data:
            return
        await self._session.execute(
            update(TorrentDownload).where(
                TorrentDownload.id == download_id
            ).values(**update_data)
        )
        await self._session.flush()

    async def update_downloads(self, download_ids: Iterable[int],
                               filter_by_statuses: list[TorrentDownloadStatus] | None = None,
                               filter_out_statuses: list[TorrentDownloadStatus] | None = None,
                               **update_data):
        if not update_data:
            return
        query = update(TorrentDownload).where(TorrentDownload.id.in_(download_ids))
        if filter_by_statuses:
            query = query.where(TorrentDownload.status.in_(filter_by_statuses))
        if filter_out_statuses:
            query = query.where(TorrentDownload.status.notin_(filter_out_statuses))
        await self._session.execute(
            query.values(**update_data)
        )
        await self._session.flush()

    async def delete_download(self, download_id: int):
        await self._session.execute(
            delete(TorrentDownload).where(
                TorrentDownload.id == download_id
            )
        )

    async def get_active_downloads_by_episode_id_and_part(self, tracked_anime_episode_id: int, episode_part: int,
                                                          episode_part_ceiling: int | None = None,
                                                          exclude_download_ids: list[int] | None = None,
                                                          created_at_after: datetime | None = None,
                                                          created_at_tiebreak_id: int | None = None,
                                                          load_relations: bool = False,
                                                          only: Iterable[str] | None = None) -> list[TorrentDownload]:
        query = select(TorrentDownload).join(Torrent).where(
            Torrent.tracked_anime_episode_id == tracked_anime_episode_id,
            Torrent.episode_part == episode_part,
            TorrentDownload.status.notin_([TorrentDownloadStatus.DELETED, TorrentDownloadStatus.DISCARDED]),
        )
        if episode_part_ceiling is not None:
            query = query.where(Torrent.episode_part_ceiling == episode_part_ceiling)
        if created_at_after:
            if created_at_tiebreak_id is not None:
                query = query.where((TorrentDownload.created_at > created_at_after) |
                                    ((TorrentDownload.created_at == created_at_after) &
                                     (TorrentDownload.id > created_at_tiebreak_id)))
            else:
                query = query.where(TorrentDownload.created_at > created_at_after)
        if exclude_download_ids:
            query = query.where(TorrentDownload.id.notin_(exclude_download_ids))
        if load_relations:
            query = query.options(joinedload(TorrentDownload.torrent)
                                  .joinedload(Torrent.tracked_anime_episode)
                                  .joinedload(TrackedAnimeEpisode.tracked_anime)
                                  .joinedload(TrackedAnime.processing_settings),
                                  joinedload(TorrentDownload.torrent)
                                  .joinedload(Torrent.tracked_anime_episode)
                                  .joinedload(TrackedAnimeEpisode.tracked_anime)
                                  .joinedload(TrackedAnime.profile))
        if only:
            query = query.options(load_only(*(getattr(TorrentDownload, column) for column in only)))
        return (await self._session.execute(query)).scalars().all()

    async def get_by_episode_id_and_part(self, tracked_anime_episode_id: int, episode_part: int | None = None,
                                         episode_part_ceiling: int | None = None, processed_only: bool = False,
                                         load_relations: bool = False) -> list[TorrentDownload]:
        query = select(TorrentDownload).join(Torrent).where(
            Torrent.tracked_anime_episode_id == tracked_anime_episode_id,
        )
        if episode_part:
            query = query.where(Torrent.episode_part == episode_part)
        if episode_part_ceiling:
            query = query.where(Torrent.episode_part_ceiling == episode_part_ceiling)
        if processed_only:
            query = query.where(TorrentDownload.status == TorrentDownloadStatus.PROCESSED)
        if load_relations:
            query = query.options(joinedload(TorrentDownload.torrent)
                                  .joinedload(Torrent.tracked_anime_episode)
                                  .joinedload(TrackedAnimeEpisode.tracked_anime)
                                  .joinedload(TrackedAnime.processing_settings))
        return (await self._session.execute(query)).scalars().all()

    # noinspection PyTypeChecker
    async def get_latest_copied_to_destination_path_at_by_torrent_space(
            self, torrent_spaces: Iterable[tuple[int, int, int]]) -> list[tuple[int, int, int, datetime]]:
        return (await self._session.execute(
            select(
                Torrent.tracked_anime_episode_id,
                Torrent.episode_part,
                Torrent.episode_part_ceiling,
                func.max(TorrentDownload.copied_to_destination_path_at),
            ).join(Torrent).where(
                tuple_(Torrent.tracked_anime_episode_id,
                       Torrent.episode_part,
                       Torrent.episode_part_ceiling).in_(torrent_spaces),
                TorrentDownload.copied_to_destination_path_at.isnot(None),
            ).group_by(
                Torrent.tracked_anime_episode_id,
                Torrent.episode_part,
                Torrent.episode_part_ceiling,
            )
        )).all()

    async def delete_downloads_by_magnet_hashes(self, magnet_hashes: list[str]):
        await self._session.execute(
            delete(TorrentDownload).where(TorrentDownload.torrent.has(Torrent.magnet_hash.in_(magnet_hashes)))
        )

    async def get_latest_created_at(self) -> datetime | None:
        return ((await self._session.execute(
            select(TorrentDownload.created_at).order_by(TorrentDownload.created_at.desc()).limit(1)
        )).scalar_one_or_none())
