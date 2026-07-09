from datetime import datetime, UTC

from sqlalchemy import select, delete
from sqlalchemy.dialects.mysql import insert

from constants import TVDBSeasonType
from dto.orm_models import TVDBSeriesEpisodes, TVDBSeries, TrackedAnimeEpisode, MappingOverride
from repositories import BaseRepo


class TVDBSeriesRepo(BaseRepo):

    # noinspection PyTypeChecker
    async def create_tvdb_series_episodes(self,
                                          tvdb_series_id: int,
                                          season_type: TVDBSeasonType,
                                          data: dict) -> TVDBSeriesEpisodes:
        tvdb_series = TVDBSeriesEpisodes(
            tvdb_series_id=tvdb_series_id,
            season_type=season_type,
            data=data
        )
        self._session.add(tvdb_series)
        await self._session.flush()
        return tvdb_series

    async def get_tvdb_series_episodes(self, tvdb_series_id: int,
                                       season_type: TVDBSeasonType) -> TVDBSeriesEpisodes | None:
        query = (select(TVDBSeriesEpisodes)
                 .where(TVDBSeriesEpisodes.tvdb_series_id == tvdb_series_id)
                 .where(TVDBSeriesEpisodes.season_type == season_type))
        return (await self._session.execute(query)).unique().scalar_one_or_none()

    async def upsert_tvdb_series_episodes(self, tvdb_series_id: int,
                                          season_type: TVDBSeasonType,
                                          data: dict | list):
        if not data:
            return
        insert_stmt = insert(TVDBSeriesEpisodes).values(
            tvdb_series_id=tvdb_series_id,
            season_type=season_type,
            data=data,
            updated_at=datetime.now(UTC)
        )
        await self._session.execute(
            insert_stmt.on_duplicate_key_update(data=data)
        )
        await self._session.flush()

    async def delete_orphaned_tvdb_series_episodes_records_updated_older_than(self, older_than: datetime):
        await self._session.execute(
            delete(TVDBSeriesEpisodes)
            .where(TVDBSeriesEpisodes.updated_at < older_than)
            .where(TVDBSeriesEpisodes.tvdb_series_id.not_in(
                select(TrackedAnimeEpisode.tvdb_series_id)
                .where(TrackedAnimeEpisode.tvdb_series_id.is_not(None))
            ))
        )
        await self._session.flush()

    async def get_tvdb_series(self, tvdb_series_id: int) -> TVDBSeries | None:
        query = (select(TVDBSeries)
                 .where(TVDBSeries.tvdb_series_id == tvdb_series_id))
        return (await self._session.execute(query)).unique().scalar_one_or_none()

    async def upsert_tvdb_series(self, tvdb_series_id: int, data: dict | list):
        if not data:
            return
        insert_stmt = insert(TVDBSeries).values(
            tvdb_series_id=tvdb_series_id,
            data=data,
            updated_at=datetime.now(UTC)
        )
        await self._session.execute(
            insert_stmt.on_duplicate_key_update(data=data)
        )
        await self._session.flush()

    async def delete_orphaned_tvdb_series_records_updated_older_than(self, older_than: datetime):
        await self._session.execute(
            delete(TVDBSeries)
            .where(TVDBSeries.updated_at < older_than)
            .where(TVDBSeries.tvdb_series_id.not_in(
                select(TrackedAnimeEpisode.tvdb_series_id)
                .where(TrackedAnimeEpisode.tvdb_series_id.is_not(None))
            ))
            .where(TVDBSeries.tvdb_series_id.not_in(
                select(MappingOverride.tvdb_series_id)
            ))
        )
        await self._session.flush()
