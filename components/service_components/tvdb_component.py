import asyncio
from datetime import timedelta, datetime, UTC

from common.db import get_session
from components.service_components import BaseServiceComponent
from constants import TVDBSeasonType
from dto.tvdb import TVDBSeriesEpisodes, TVDBSeriesSearchResult, TVDBSeries
from repositories.cache_repositories.tvdb_series_repo import TVDBSeriesRepo
from services.tvdb_service import TVDBService


class TVDBComponent(BaseServiceComponent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tvdb_service = TVDBService()

    async def search_series(self, name: str, force_fetch: bool = False) -> list[TVDBSeriesSearchResult]:
        results = await self._tvdb_service.search_series(query=name, force_fetch=force_fetch)
        return TVDBSeriesSearchResult.many_from_dict(results)

    async def get_series_episodes(self, series_id: int, season_type: TVDBSeasonType,
                                  minimum_freshness: timedelta | None = None) -> TVDBSeriesEpisodes:
        tvdb_series_repo = TVDBSeriesRepo(get_session())
        cached_episodes_record = await tvdb_series_repo.get_tvdb_series_episodes(tvdb_series_id=series_id,
                                                                                 season_type=season_type)
        if (cached_episodes_record and
                (minimum_freshness is None
                 or cached_episodes_record.updated_at > datetime.now(UTC) - minimum_freshness)):
            return TVDBSeriesEpisodes.from_episode_list(series_id=series_id,
                                                        season_type=season_type,
                                                        episodes=cached_episodes_record.data)  # type: ignore

        return await self.fetch_series_episodes(series_id=series_id, season_type=season_type)

    async def fetch_series_episodes(self, series_id: int, season_type: TVDBSeasonType) -> TVDBSeriesEpisodes:
        page = 0
        episodes = []
        while True:
            response = await self._tvdb_service.get_series_episodes(series_id=series_id, season_type=season_type,
                                                                    page=page)
            episodes.extend(response['data']['episodes'])
            if response['links']['next'] is None or not response['data']['episodes']:
                break
            page += 1
            await asyncio.sleep(0.2)

        await TVDBSeriesRepo(get_session()).upsert_tvdb_series_episodes(tvdb_series_id=series_id,
                                                                        season_type=season_type,
                                                                        data=episodes)

        return TVDBSeriesEpisodes.from_episode_list(series_id=series_id,
                                                    season_type=season_type,
                                                    episodes=episodes)

    async def get_series(self, series_id: int,
                         minimum_freshness: timedelta | None = None) -> TVDBSeries:
        tvdb_series_repo = TVDBSeriesRepo(get_session())
        cached_record = await tvdb_series_repo.get_tvdb_series(tvdb_series_id=series_id)
        if (cached_record and
                (minimum_freshness is None
                 or cached_record.updated_at > datetime.now(UTC) - minimum_freshness)):
            return TVDBSeries.from_dict(data=cached_record.data)

        return await self.fetch_series(series_id=series_id)

    async def fetch_series(self, series_id: int) -> TVDBSeries:
        series_data = (await self._tvdb_service.get_series(series_id=series_id))['data']
        translations = (await self._tvdb_service.get_series_translations(series_id=series_id))['data']
        series_data['eng_translation'] = translations

        await TVDBSeriesRepo(get_session()).upsert_tvdb_series(tvdb_series_id=series_id,
                                                               data=series_data)
        return TVDBSeries.from_dict(data=series_data)
