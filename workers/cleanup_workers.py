import asyncio
from datetime import datetime, UTC, timedelta

import app_state
from app_state import anime_relations
from common.db import get_session
from common.http_session import _async_http_sessions, _sync_http_sessions  # noqa
from common.decorators import periodic_worker, require_db_session
from components.external_image_component import ExternalImageComponent
from components.service_components.anilist_component import AnilistComponent
from components.service_components.anilist_list_component import AnilistListComponent
from config import config
from repositories.cache_repositories.anilist_anime_repo import AnilistAnimeRepo
from repositories.cache_repositories.anilist_anime_airing_schedule_repo import AnilistAnimeAiringScheduleRepo
from repositories.cache_repositories.tvdb_series_repo import TVDBSeriesRepo
from workers import BaseWorkerClass


class CleanupWorkers(BaseWorkerClass):
    NAME = "Cleaners & Refreshers"

    def __init__(self):
        super().__init__()
        self._cleanup_in_memory_caches_run_count = 0

    @periodic_worker(frequency=600, initial_delay=10)
    async def cleanup_in_memory_caches(self):
        from app_state import CACHED_RESPONSES
        obsolete_async_session_names = []
        obsolete_sync_session_names = []
        for session_name, (session, expiry) in _async_http_sessions.items():
            if expiry < datetime.now(UTC):
                obsolete_async_session_names.append(session_name)
                await session.close()
        for session_name in obsolete_async_session_names:
            _async_http_sessions.pop(session_name, None)
        for session_name, (session, expiry) in _sync_http_sessions.items():
            if expiry < datetime.now(UTC):
                obsolete_sync_session_names.append(session_name)
                session.close()
        for session_name in obsolete_sync_session_names:
            _sync_http_sessions.pop(session_name, None)

        obsolete_web_responses_keys = []
        for cache_key, cached_response in CACHED_RESPONSES.items():
            if cached_response.cache_expiry < datetime.now(UTC):
                obsolete_web_responses_keys.append(cache_key)
        for cache_key in obsolete_web_responses_keys:
            CACHED_RESPONSES.pop(cache_key, None)

        obsolete_anilist_search_minimal_result_keys = []
        for cache_key, cached_result in app_state.ANILIST_TITLE_SEARCH_MINIMAL_RESULT.items():
            if cached_result.last_accessed < (datetime.now(UTC) - timedelta(days=7)):
                obsolete_anilist_search_minimal_result_keys.append(cache_key)
        for cache_key in obsolete_anilist_search_minimal_result_keys:
            app_state.ANILIST_TITLE_SEARCH_MINIMAL_RESULT.pop(cache_key, None)

        if self._cleanup_in_memory_caches_run_count % 30 == 0:
            app_state.ANILIST_TITLE_SEARCH_NOT_FOUND.clear()

        self._cleanup_in_memory_caches_run_count += 1

    @periodic_worker(frequency=60*60*24, initial_delay=60*10)
    @require_db_session
    async def refresh_anime_relations_cache(self):
        await anime_relations.refresh_relations()

    @periodic_worker(frequency=60*60*1, initial_delay=60)
    @require_db_session
    async def refresh_stale_db_data(self):
        anime_data_older_than_3_days = await AnilistAnimeRepo(get_session()).\
            get_updated_older_than(datetime.now(UTC) - timedelta(days=3))
        anilist_anime_ids = [anime.anilist_id for anime in anime_data_older_than_3_days]
        for i in range(0, len(anilist_anime_ids), 50):
            await AnilistComponent().fetch_anime_records(
                anilist_anime_ids=anilist_anime_ids[i:i+50],
            )
            if i + 50 < len(anilist_anime_ids):
                await asyncio.sleep(10)  # be very patient

    @periodic_worker(frequency=60*60*24, initial_delay=600)
    @require_db_session
    async def cleanup_db_and_disk_cache(self):
        await AnilistAnimeRepo(get_session()).\
            delete_orphans_updated_older_than(datetime.now(UTC) - timedelta(days=90))
        await AnilistAnimeRepo(get_session()). \
            delete_orphan_extras_updated_older_than(datetime.now(UTC) - timedelta(days=14))
        await AnilistAnimeAiringScheduleRepo(get_session()). \
            delete_updated_older_than(datetime.now(UTC) - timedelta(days=60))
        await AnilistAnimeAiringScheduleRepo(get_session()). \
            delete_airing_at_older_than(int((datetime.now(UTC) - timedelta(days=3)).timestamp()))
        await AnilistAnimeAiringScheduleRepo(get_session()). \
            delete_monthly_updated_older_than(datetime.now(UTC) - timedelta(days=90))
        await TVDBSeriesRepo(get_session()). \
            delete_orphaned_tvdb_series_episodes_records_updated_older_than(datetime.now(UTC) - timedelta(days=90))
        await TVDBSeriesRepo(get_session()). \
            delete_orphaned_tvdb_series_records_updated_older_than(datetime.now(UTC) - timedelta(days=90))
        await ExternalImageComponent().cleanup_expired_images()

    @periodic_worker(frequency=60*10, initial_delay=60)
    @require_db_session
    async def refresh_anime_user_lists(self):
        if not config.user_settings.anilist_user_token:
            return
        await AnilistListComponent().fetch_user_anime_list()
