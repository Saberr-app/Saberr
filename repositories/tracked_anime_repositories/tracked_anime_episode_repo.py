from typing import Iterable

from sqlalchemy import select, update, delete
from sqlalchemy.orm import joinedload

from dto.orm_models import TrackedAnimeEpisode, Torrent
from repositories import BaseRepo


class TrackedAnimeEpisodeRepo(BaseRepo):

    # noinspection PyTypeChecker
    async def create_tracked_anime_episode(self,
                                           tracked_anime_id: int,
                                           episode_number: int,
                                           tvdb_series_id: int | None,
                                           tvdb_season_number: int | None,
                                           tvdb_episode_numbers: list,
                                           tvdb_episode_ids: list,
                                           tvdb_episode_part: int | None,
                                           tvdb_episode_part_ceiling: int | None,
                                           auto_discard: bool = False) -> TrackedAnimeEpisode:
        tracked_anime_episode = TrackedAnimeEpisode(
            tracked_anime_id=tracked_anime_id,
            episode_number=episode_number,
            tvdb_series_id=tvdb_series_id,
            tvdb_season_number=tvdb_season_number,
            tvdb_episode_numbers=tvdb_episode_numbers,
            tvdb_episode_ids=tvdb_episode_ids,
            tvdb_episode_part=tvdb_episode_part,
            tvdb_episode_part_ceiling=tvdb_episode_part_ceiling,
            auto_discard=auto_discard
        )
        self._session.add(tracked_anime_episode)
        await self._session.flush()
        return tracked_anime_episode

    async def get_tracked_anime_episode(self,
                                        tracked_anime_id: int,
                                        episode_number: int,
                                        load_relations: bool = False) -> TrackedAnimeEpisode | None:
        query = select(TrackedAnimeEpisode).where(
            TrackedAnimeEpisode.tracked_anime_id == tracked_anime_id,
            TrackedAnimeEpisode.episode_number == episode_number
        )
        if load_relations:
            query = query.options(
                joinedload(TrackedAnimeEpisode.tracked_anime),
                joinedload(TrackedAnimeEpisode.torrents).joinedload(Torrent.download),
                joinedload(TrackedAnimeEpisode.torrents).joinedload(Torrent.parent_torrent).joinedload(Torrent.download)
            )
        return (await self._session.execute(query)).unique().scalar_one_or_none()

    async def get_tracked_anime_episode_list(self,
                                             tracked_anime_id: int,
                                             load_relations: bool = False) -> list[TrackedAnimeEpisode]:
        query = select(TrackedAnimeEpisode).where(TrackedAnimeEpisode.tracked_anime_id == tracked_anime_id)
        if load_relations:
            query = query.options(
                joinedload(TrackedAnimeEpisode.tracked_anime),
                joinedload(TrackedAnimeEpisode.torrents).joinedload(Torrent.download),
                joinedload(TrackedAnimeEpisode.torrents).joinedload(Torrent.parent_torrent).joinedload(Torrent.download)
            )
        return (await self._session.execute(query)).unique().scalars().all()

    async def update_tracked_anime_episode(self, tracked_anime_episode_id: int, **update_data):
        if not update_data:
            return
        await self._session.execute(
            update(TrackedAnimeEpisode).where(TrackedAnimeEpisode.id == tracked_anime_episode_id).values(**update_data)
        )
        await self._session.flush()

    async def update_tracked_anime_episodes(self, tracked_anime_episode_ids: Iterable[int], **update_data):
        if not update_data:
            return
        await self._session.execute(
            update(TrackedAnimeEpisode)
            .where(TrackedAnimeEpisode.id.in_(tracked_anime_episode_ids))
            .values(**update_data)
        )
        await self._session.flush()

    async def delete_tracked_anime_episode(self, tracked_anime_episode_id: int):
        await self._session.execute(
            delete(TrackedAnimeEpisode).where(TrackedAnimeEpisode.id == tracked_anime_episode_id)
        )
