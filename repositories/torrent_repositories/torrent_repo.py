from typing import Iterable

from sqlalchemy import select, update, delete
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import joinedload

from system import UNSET
from constants import VideoSource, Resolution, Encoding
from dto.orm_models import Torrent, TrackedAnimeEpisode, TrackedAnime
from repositories import BaseRepo


class TorrentRepo(BaseRepo):

    # noinspection PyTypeChecker
    async def create_torrent(self,
                             tracked_anime_episode_id: int,
                             parent_torrent_id: int | None,
                             magnet_hash: str,
                             rss_xml: str,
                             torrent_link: str,
                             torrent_title: str,
                             override: bool,
                             discarded: bool,
                             release_group: str,
                             title: str,
                             episode_number: int,
                             episode_part: int,
                             episode_part_ceiling: int,
                             language_code: str,
                             encoding: Encoding,
                             resolution: Resolution,
                             version_number: int,
                             repack_indicator: bool,
                             source: VideoSource) -> Torrent:
        torrent = Torrent(
            tracked_anime_episode_id=tracked_anime_episode_id,  # noqa
            parent_torrent_id=parent_torrent_id,
            magnet_hash=magnet_hash,
            rss_xml=rss_xml,
            torrent_link=torrent_link,
            torrent_title=torrent_title,
            override=override,
            discarded=discarded,
            release_group=release_group,
            title=title,
            episode_number=episode_number,
            episode_part=episode_part,
            episode_part_ceiling=episode_part_ceiling,
            language_code=language_code,
            encoding=encoding,
            resolution=resolution,
            version_number=version_number,
            repack_indicator=repack_indicator,
            source=source
        )
        self._session.add(torrent)
        await self._session.flush()
        return torrent

    async def get_torrent(self,
                          torrent_id: int,
                          load_relations: bool = False) -> Torrent | None:
        query = select(Torrent)
        if torrent_id:
            query = query.where(Torrent.id == torrent_id)
        if load_relations:
            query = query.options(
                joinedload(Torrent.tracked_anime_episode)
                .joinedload(TrackedAnimeEpisode.tracked_anime),
                joinedload(Torrent.download),
                joinedload(Torrent.parent_torrent).joinedload(Torrent.download)
            )
        return (await self._session.execute(query)).unique().scalar_one_or_none()

    async def get_torrents_by_tracked_anime_episode_ids(self,
                                                        episode_ids: Iterable[int],
                                                        exclude_discarded: bool = True,
                                                        load_relations: bool = False) -> list[Torrent]:
        if not episode_ids:
            return []
        query = select(Torrent).where(
            Torrent.tracked_anime_episode_id.in_(episode_ids)
        )
        if exclude_discarded:
            query = query.where(Torrent.discarded == 0)
        if load_relations:
            query = query.options(
                joinedload(Torrent.tracked_anime_episode)
                .joinedload(TrackedAnimeEpisode.tracked_anime).joinedload(TrackedAnime.profile),
                joinedload(Torrent.download),
                joinedload(Torrent.parent_torrent).joinedload(Torrent.download)
            )
        return (await self._session.execute(query)).unique().scalars().all()

    async def get_torrents_by_hashes(self,
                                     magnet_hashes: Iterable[str],
                                     discarded: bool = None,
                                     parent_torrent_id: int | None = UNSET,
                                     load_relations: bool = False) -> list[Torrent]:
        query = select(Torrent).where(
            Torrent.magnet_hash.in_(magnet_hashes)
        )
        if discarded is not None:
            query = query.where(Torrent.discarded == discarded)
        if parent_torrent_id is not UNSET:
            if parent_torrent_id is None:
                query = query.where(Torrent.parent_torrent_id.is_(None))
            else:
                query = query.where(Torrent.parent_torrent_id == parent_torrent_id)
        if load_relations:
            query = query.options(
                joinedload(Torrent.tracked_anime_episode)
                .joinedload(TrackedAnimeEpisode.tracked_anime).joinedload(TrackedAnime.processing_settings),
                joinedload(Torrent.tracked_anime_episode)
                .joinedload(TrackedAnimeEpisode.tracked_anime).joinedload(TrackedAnime.profile),
                joinedload(Torrent.download),
                joinedload(Torrent.parent_torrent).joinedload(Torrent.download)
            )
        return (await self._session.execute(query)).unique().scalars().all()

    async def get_torrents_by_parent_ids(self,
                                         parent_ids: Iterable[int],
                                         load_relations: bool = False) -> list[Torrent]:
        if not parent_ids:
            return []
        query = select(Torrent).where(
            Torrent.parent_torrent_id.in_(parent_ids)
        )
        if load_relations:
            query = query.options(
                joinedload(Torrent.tracked_anime_episode)
                .joinedload(TrackedAnimeEpisode.tracked_anime).joinedload(TrackedAnime.processing_settings),
                joinedload(Torrent.tracked_anime_episode)
                .joinedload(TrackedAnimeEpisode.tracked_anime).joinedload(TrackedAnime.profile),
                joinedload(Torrent.download)
            )
        return (await self._session.execute(query)).unique().scalars().all()

    async def update_torrent(self, torrent_id: int, **update_data):
        if not update_data:
            return
        await self._session.execute(
            update(Torrent).where(
                Torrent.id == torrent_id
            ).values(**update_data)
        )
        await self._session.flush()

    async def bulk_update_torrents(self, data: list[dict]):
        if not data:
            return
        await self._session.execute(update(Torrent), data)
        await self._session.flush()

    async def upsert_torrent(self, magnet_hash: str, tracked_anime_episode_id: int, **update_data):
        if not update_data:
            return
        insert_stmt = insert(Torrent).values(
            magnet_hash=magnet_hash,
            tracked_anime_episode_id=tracked_anime_episode_id,
            **update_data
        )
        await self._session.execute(
            insert_stmt.on_duplicate_key_update(**update_data)
        )
        await self._session.flush()

    async def delete_torrent(self, torrent_id: int):
        await self._session.execute(
            delete(Torrent).where(
                Torrent.id == torrent_id
            )
        )

    async def delete_torrents(self, torrent_ids: list[int]):
        if not torrent_ids:
            return
        await self._session.execute(
            delete(Torrent).where(
                Torrent.id.in_(torrent_ids)
            )
        )

    async def update_torrents_by_magnet_hashes(self, magnet_hashes: Iterable[str], **data):
        if not magnet_hashes:
            return
        await self._session.execute(
            update(Torrent).where(
                Torrent.magnet_hash.in_(magnet_hashes)
            ).values(**data)
        )
        await self._session.flush()
