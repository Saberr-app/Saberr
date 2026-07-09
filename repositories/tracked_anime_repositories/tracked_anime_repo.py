from typing import Iterable

from sqlalchemy import select, update, delete, tuple_
from sqlalchemy.orm import joinedload, contains_eager

from constants import TrackedAnimeStatus, TVDBSeasonType
from dto.orm_models import TrackedAnime, TrackedAnimeEpisode, Torrent, TrackedAnimeReleaseGroupPreferences
from repositories import BaseRepo


class TrackedAnimeRepo(BaseRepo):

    # noinspection PyTypeChecker
    async def create_tracked_anime(self,
                                   romaji_title: str,
                                   native_title: str | None,
                                   english_title: str | None,
                                   anilist_id: int,
                                   status: TrackedAnimeStatus,
                                   from_episode: int,
                                   show_parent_directory: str,
                                   show_folder_name: str,
                                   tracked_anime_profile_id: int = 1,
                                   tvdb_structure_enabled: bool = False,
                                   tvdb_season_type: TVDBSeasonType = TVDBSeasonType.OFFICIAL) -> TrackedAnime:
        tracked_anime = TrackedAnime(
            romaji_title=romaji_title,
            native_title=native_title,
            english_title=english_title,
            anilist_id=anilist_id,
            status=status,
            from_episode=from_episode,
            tvdb_structure_enabled=tvdb_structure_enabled,
            tvdb_season_type=tvdb_season_type,
            show_parent_directory=show_parent_directory,
            show_folder_name=show_folder_name,
            tracked_anime_profile_id=tracked_anime_profile_id  # noqa
        )
        self._session.add(tracked_anime)
        await self._session.flush()
        return tracked_anime

    async def get_tracked_anime(self,
                                tracked_anime_id: int | None = None,
                                anilist_id: int | None = None,
                                load_relations: bool = False) -> TrackedAnime | None:
        query = select(TrackedAnime)
        if tracked_anime_id is not None:
            query = query.where(TrackedAnime.id == tracked_anime_id)
        elif anilist_id is not None:
            query = query.where(TrackedAnime.anilist_id == anilist_id)
        else:
            raise ValueError("At least one identifier must be provided")
        if load_relations:
            query = query.options(
                joinedload(TrackedAnime.processing_settings),
                joinedload(TrackedAnime.profile),
                joinedload(TrackedAnime.release_groups_preferences),
                joinedload(TrackedAnime.episodes).joinedload(TrackedAnimeEpisode.torrents).joinedload(Torrent.download),
                joinedload(TrackedAnime.episodes).joinedload(TrackedAnimeEpisode.torrents)
                .joinedload(Torrent.parent_torrent).joinedload(Torrent.download)
            )
        return (await self._session.execute(query)).unique().scalar_one_or_none()

    async def get_tracked_anime_list(self,
                                     tracked_anime_ids: Iterable[int] | None = None,
                                     anilist_ids: Iterable[int] | None = None,
                                     load_relations: bool = False) -> list[TrackedAnime]:
        if tracked_anime_ids is None and anilist_ids is None:
            raise ValueError("At least one identifier must be provided")
        if not tracked_anime_ids and not anilist_ids:
            return []
        query = select(TrackedAnime)
        if tracked_anime_ids is not None:
            query = query.where(TrackedAnime.id.in_(tracked_anime_ids))
        elif anilist_ids is not None:
            query = query.where(TrackedAnime.anilist_id.in_(anilist_ids))
        if load_relations:
            query = query.options(
                joinedload(TrackedAnime.processing_settings),
                joinedload(TrackedAnime.profile),
                joinedload(TrackedAnime.release_groups_preferences),
                joinedload(TrackedAnime.episodes).joinedload(TrackedAnimeEpisode.torrents).joinedload(Torrent.download),
                joinedload(TrackedAnime.episodes).joinedload(TrackedAnimeEpisode.torrents)
                .joinedload(Torrent.parent_torrent).joinedload(Torrent.download)
            )
        return (await self._session.execute(query)).unique().scalars().all()

    async def get_all_tracked_anime(self,
                                    anilist_ids: Iterable[int] | None = None,
                                    load_relations: bool = False,
                                    statuses: Iterable[TrackedAnimeStatus] | None = None) -> list[TrackedAnime]:
        query = select(TrackedAnime).where(TrackedAnime.status.in_(statuses))
        if anilist_ids is not None:
            query = query.where(TrackedAnime.anilist_id.in_(anilist_ids))
        if load_relations:
            query = query.options(
                joinedload(TrackedAnime.processing_settings),
                joinedload(TrackedAnime.profile),
                joinedload(TrackedAnime.release_groups_preferences),
                joinedload(TrackedAnime.episodes).joinedload(TrackedAnimeEpisode.torrents).joinedload(Torrent.download),
                joinedload(TrackedAnime.episodes).joinedload(TrackedAnimeEpisode.torrents)
                .joinedload(Torrent.parent_torrent).joinedload(Torrent.download)
            )
        return (await self._session.execute(query)).unique().scalars().all()

    async def update_tracked_anime(self, tracked_anime_id: int, **update_data):
        if not update_data:
            return
        await self._session.execute(
            update(TrackedAnime).where(TrackedAnime.id == tracked_anime_id).values(**update_data)
        )
        await self._session.flush()

    async def batch_update_tracked_anime(self, update_mappings: list[dict]):
        if not update_mappings:
            return
        await self._session.execute(update(TrackedAnime), update_mappings)
        await self._session.flush()

    async def delete_tracked_anime(self, tracked_anime_id: int):
        await self._session.execute(
            delete(TrackedAnime).where(TrackedAnime.id == tracked_anime_id)
        )

    async def get_release_group_preferences_for_overriding_titles(
            self,
            title_release_group_pairs: Iterable[tuple[str, str]]
    ) -> list[TrackedAnimeReleaseGroupPreferences]:
        pairs = list(title_release_group_pairs)
        if not pairs:
            return []
        query = select(TrackedAnimeReleaseGroupPreferences) \
            .join(TrackedAnimeReleaseGroupPreferences.tracked_anime) \
            .options(contains_eager(TrackedAnimeReleaseGroupPreferences.tracked_anime)) \
            .where(tuple_(TrackedAnimeReleaseGroupPreferences.override_match_against,
                          TrackedAnimeReleaseGroupPreferences.release_group).in_(pairs)) \
            .order_by(TrackedAnime.status.asc(), TrackedAnime.anilist_id.desc())
        return (await self._session.execute(query)).unique().scalars().all()
