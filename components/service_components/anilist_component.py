import asyncio
import re
from collections import defaultdict
from datetime import datetime, timedelta, UTC
from typing import Iterable

import app_state
from common.context_helpers import create_task
from common.db import get_session
from common.exceptions import ExternalServiceException
from components.service_components import BaseServiceComponent
from constants import AnilistAnimeSeason, AnilistAnimeStatus, AnilistAnimeFormat, AnilistAnimeSource
from dto.anilist import AnilistAnime, AnilistAnimeMinimal
from repositories.cache_repositories.anilist_anime_repo import AnilistAnimeRepo
from services.anilist_service import AnilistService


class AnilistComponent(BaseServiceComponent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._anilist_service = AnilistService()

    async def get_anime_records(self, anilist_anime_ids: Iterable[int],
                                force_refresh: bool = False) -> list[AnilistAnime]:
        anilist_anime_db_records = await AnilistAnimeRepo(get_session()).get_anilist_anime_list(anilist_anime_ids)
        anilist_anime_records = AnilistAnime.many_from_dict(
            [db_record.data for db_record in anilist_anime_db_records if not force_refresh]
        )

        # missing or stale ids fall through to a fresh fetch
        missing_ids = set(anilist_anime_ids) - {anime.id for anime in anilist_anime_records}
        if missing_ids:
            fetched_anime_records = await self.fetch_anime_records(list(missing_ids))
            anilist_anime_records.extend(fetched_anime_records)
        return anilist_anime_records

    async def fetch_anime_records(self, anilist_anime_ids: list[int]) -> list[AnilistAnime]:
        from components.operational_components.tracked_anime_component import TrackedAnimeComponent
        if not anilist_anime_ids:
            return []
        anilist_anime_ids = list(set(anilist_anime_ids))
        fetched_anime_records = []
        for i in range(0, len(anilist_anime_ids), 50):
            fetched_anime_records.extend(
                await self._anilist_service.get_anime_data(anilist_anime_ids=anilist_anime_ids[i:i + 50])
            )
            if i + 50 < len(anilist_anime_ids):
                await asyncio.sleep(0.5)

        await self.persist_anilist_anime_in_db(fetched_anime_records)
        fetched_anime_records = AnilistAnime.many_from_dict(fetched_anime_records)
        create_task(TrackedAnimeComponent().update_tracked_anime_from_anilist(fetched_anime_records))
        return fetched_anime_records

    async def get_anime(self, anilist_anime_id: int,
                        raise_on_service_error: bool = True,
                        force_refresh: bool = False) -> AnilistAnime | None:
        try:
            anime_records = await self.get_anime_records([anilist_anime_id],
                                                         force_refresh=force_refresh)
        except ExternalServiceException as e:
            if raise_on_service_error:
                raise e
            return None
        if anime_records:
            return anime_records[0]
        return None

    async def get_anime_with_filters(self,
                                     query: str | None = None,
                                     statuses: list[AnilistAnimeStatus] | None = None,
                                     season: AnilistAnimeSeason | None = None,
                                     season_year: int | None = None,
                                     formats: list[AnilistAnimeFormat] | None = None,
                                     sources: list[AnilistAnimeSource] | None = None,
                                     genres: list[str] | None = None,
                                     tags: list[str] | None = None,
                                     exclude_genres: list[str] | None = None,
                                     exclude_tags: list[str] | None = None,
                                     on_list: bool | None = None,
                                     per_page: int = 50,
                                     page: int = 1,
                                     sort: list[str] | None = None,
                                     force_fetch: bool = False) -> list[AnilistAnime]:
        anime_data_list = await self._anilist_service.search_anime(query=query,
                                                                   statuses=statuses,
                                                                   season=season,
                                                                   season_year=season_year,
                                                                   formats=formats,
                                                                   sources=sources,
                                                                   genres=genres,
                                                                   tags=tags,
                                                                   exclude_genres=exclude_genres,
                                                                   exclude_tags=exclude_tags,
                                                                   on_list=on_list,
                                                                   per_page=per_page,
                                                                   page=page,
                                                                   sort=sort,
                                                                   force_fetch=force_fetch)
        await self.persist_anilist_anime_in_db(anime_data_list)
        return AnilistAnime.many_from_dict(anime_data_list)

    # noinspection PyMethodMayBeStatic
    async def persist_anilist_anime_in_db(self, fetched_anime_records: list[dict]):
        await AnilistAnimeRepo(get_session()).bulk_upsert_anilist_anime(
            data_list=[
                {
                    "anilist_id": anime["id"],
                    "data": anime,
                } for anime in fetched_anime_records
            ]
        )

    async def get_anime_multi_search_results(self, queries: list[str],
                                             force_fetch: bool = False) -> dict[str, AnilistAnimeMinimal]:
        queries = set(queries)
        normalized_query_query_map = defaultdict(list)
        for query in queries:
            normalized_query = query.lower().rstrip('.').strip()
            normalized_query_query_map[normalized_query].append(query)
            if re.search(r's\d+$', normalized_query):
                season_normalized_query = re.sub(r's(\d+)$', r'season \1', normalized_query)
                normalized_query_query_map[season_normalized_query].append(query)
            if re.search(r'season \d+$', normalized_query):
                season_normalized_query = re.sub(r'season (\d+)$', r's\1', normalized_query)
                normalized_query_query_map[season_normalized_query].append(query)
        normalized_queries = list(normalized_query_query_map.keys())
        if force_fetch:
            titles_to_fetch = list(normalized_queries)
        else:
            titles_to_fetch = [query for query in normalized_queries
                               if (query not in app_state.ANILIST_TITLE_SEARCH_MINIMAL_RESULT
                                   or app_state.ANILIST_TITLE_SEARCH_MINIMAL_RESULT[query].expired)
                               and query not in app_state.ANILIST_TITLE_SEARCH_NOT_FOUND]
        for i in range(0, len(titles_to_fetch), 50):
            try:
                query_data = await self._anilist_service.multi_search_anime(queries=titles_to_fetch[i:i + 50],
                                                                            force_fetch=True)
                for query, data in query_data.items():
                    if not data:
                        app_state.ANILIST_TITLE_SEARCH_NOT_FOUND.add(query)
                        continue
                    anime_min = AnilistAnimeMinimal.from_dict(data)
                    app_state.ANILIST_TITLE_SEARCH_MINIMAL_RESULT[query] = anime_min
            except ExternalServiceException as e:
                self.logger.error(f"Error while fetching anime search results for queries {titles_to_fetch}: {e}")
            if i + 50 < len(titles_to_fetch):
                await asyncio.sleep(0.5)
        result = {}
        for normalized_query in normalized_queries:
            for query in normalized_query_query_map[normalized_query]:
                anime_min = app_state.ANILIST_TITLE_SEARCH_MINIMAL_RESULT.get(normalized_query)
                if anime_min is not None or result.get(query) is None:
                    result[query] = anime_min
        return result

    async def get_anime_extras(self, anilist_id: int, force_fetch: bool = False) -> dict:
        db_record = await AnilistAnimeRepo(get_session()).get_anilist_anime_extras(anilist_id=anilist_id)

        if not db_record or db_record.updated_at < (datetime.now(UTC) - timedelta(days=7)) or force_fetch:
            data = await self._anilist_service.get_anime_extra_data(anilist_id=anilist_id)
            await AnilistAnimeRepo(get_session()).upsert_anilist_anime_extras(anilist_id=anilist_id, data=data)
            return data
        else:
            return db_record.data
