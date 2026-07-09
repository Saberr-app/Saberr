import asyncio
from datetime import timedelta

from api.schemas.schedule_schemas import AiringScheduleListRequest, AiringScheduleListResponse, AiringScheduleItem
from common.decorators import api_component
from common.exceptions import BadRequestException
from components import BaseComponent
from components.service_components.anilist_component import AnilistComponent
from components.service_components.anilist_list_component import AnilistListComponent
from components.operational_components.tracked_anime_component import TrackedAnimeComponent
from components.service_components.anilist_airing_schedule_component import AnilistAiringScheduleComponent
from config import config
from constants import AiringScheduleScope, AnilistAnimeStatus, TorrentDownloadStatus, \
    TORRENT_DOWNLOAD_STATUS_PRIORITY_LIST
from api.schemas.anime_schemas import AnimeListRequest
from services.anilist_service import AnilistService
from utils.helpers.date_helpers import get_current_season_and_year, get_next_season_and_year


class ScheduleAPIComponent(BaseComponent):

    def __init__(self):
        super().__init__()
        self._anilist_component = AnilistComponent()
        self._anilist_list_component = AnilistListComponent()
        self._anilist_service = AnilistService()
        self._tracked_anime_component = TrackedAnimeComponent()
        self._anilist_airing_schedule_component = AnilistAiringScheduleComponent()

    @api_component
    async def get_airing_schedule(self, params: AiringScheduleListRequest) -> AiringScheduleListResponse:
        if params.day:
            from_datetime = params.day
            to_datetime = params.day + timedelta(days=1)
        elif params.week:
            from_datetime = params.week
            to_datetime = params.week + timedelta(days=7)
        elif params.month:
            from_datetime = params.month
            to_month, to_year = params.month.month + 1, params.month.year
            if to_month > 12:
                to_month = 1
                to_year += 1
            to_datetime = params.month.replace(month=to_month, year=to_year)
        else:
            raise BadRequestException("Either day, week or month must be specified")
        if not params.scope:
            raise BadRequestException("Scope must be specified")

        user_list = await self._anilist_list_component.get_user_anime_list(force_fetch=params.force_refresh) \
            if config.user_settings.anilist_user_token else None
        tracked_anime_list = await self._tracked_anime_component.get_all_tracked_anime()
        anilist_id_tracked_anime_map = {tracked_anime.anilist_id: tracked_anime for tracked_anime in tracked_anime_list}

        scope = set(params.scope)
        anilist_ids = set()
        if AiringScheduleScope.USER_WATCHING in scope and user_list:
            anilist_ids.update(user_list.current_anime_ids)
        if AiringScheduleScope.USER_PLANNING in scope and user_list:
            anilist_ids.update(user_list.planning_anime_ids)
        if AiringScheduleScope.USER_TRACKING in scope and tracked_anime_list:
            anilist_ids.update(anilist_id_tracked_anime_map.keys())
        seasons = []
        if AiringScheduleScope.CURRENT_SEASON in scope:
            seasons.append(get_current_season_and_year())
        if AiringScheduleScope.NEXT_SEASON in scope:
            seasons.append(get_next_season_and_year())
        for season, season_year in seasons:
            for page in range(1, 5):  # unlikely to go over 3 pages
                anime_data_list = await self._anilist_service.search_anime(season=season,
                                                                           season_year=season_year,
                                                                           page=page,
                                                                           sort=[AnimeListRequest.AnimeSortBy.ID.value],
                                                                           force_fetch=params.force_refresh)
                anilist_ids.update({anime_data["id"] for anime_data in anime_data_list})
                if len(anime_data_list) < 50:
                    break
                if not self._anilist_service.cache_hit_on_last_request():
                    await asyncio.sleep(1)
        if AiringScheduleScope.ALL_AIRING in scope:
            for page in range(1, 10):
                anime_data_list = await self._anilist_service.search_anime(statuses=[AnilistAnimeStatus.RELEASING],
                                                                           page=page,
                                                                           sort=[AnimeListRequest.AnimeSortBy.ID.value],
                                                                           force_fetch=params.force_refresh)
                anilist_ids.update({anime_data["id"] for anime_data in anime_data_list})
                if len(anime_data_list) < 50:
                    break
                if not self._anilist_service.cache_hit_on_last_request():
                    await asyncio.sleep(1)

        anime_records = await self._anilist_component.get_anime_records(
            anilist_anime_ids=anilist_ids,
            force_refresh=params.force_refresh,
        )
        anilist_id_anime_map = {anime_record.id: anime_record for anime_record in anime_records}
        # try to filter out anime whose start/finish date is out of range from being sent
        for anilist_id, anime_record in anilist_id_anime_map.items():
            start_date = anime_record.start_date.parsed_date(floor_null=True)
            end_date = anime_record.end_date.parsed_date(ceil_null=True)
            if start_date and start_date > to_datetime:
                anilist_ids.discard(anilist_id)
            if end_date and end_date < from_datetime:
                anilist_ids.discard(anilist_id)

        schedules = await self._anilist_airing_schedule_component.get_airing_schedules_in_range(
            from_date=from_datetime,
            to_date=to_datetime,
            anilist_anime_ids=anilist_ids,
            force_fetch=params.force_refresh,
        )

        # resolve the optimistic download status
        episode_download_status_map: dict[tuple[int, int], TorrentDownloadStatus] = {}
        for anilist_id, tracked_anime in anilist_id_tracked_anime_map.items():
            for episode in tracked_anime.episodes:
                statuses = [torrent.effective_download.status for torrent in episode.torrents
                            if torrent.effective_download]
                if not statuses:
                    continue
                episode_download_status_map[(anilist_id, episode.episode_number)] = \
                    min(statuses, key=TORRENT_DOWNLOAD_STATUS_PRIORITY_LIST.index)

        airing_schedule_items = []
        anime_items = []
        for anilist_id, anime_schedules in schedules.items():
            anime_record = anilist_id_anime_map.get(anilist_id)
            if not anime_record or not anime_schedules:
                continue
            for schedule in anime_schedules:
                download_status = episode_download_status_map.get((anilist_id, schedule.episode))
                download_status = download_status if download_status not in {TorrentDownloadStatus.DELETED,
                                                                             TorrentDownloadStatus.DISCARDED} else None
                airing_schedule_items.append(AiringScheduleItem(
                    id=anilist_id * 10000 + schedule.episode,
                    anilist_id=anilist_id,
                    airing_at=schedule.airing_at,
                    episode=schedule.episode,
                    title=None,
                    download_status=download_status
                ))
            user_entry = user_list.get_entry_by_anime_id(anilist_id) if user_list else None
            tracked_anime = anilist_id_tracked_anime_map.get(anilist_id)
            anime_items.append(AiringScheduleListResponse.AnimeItem(
                anilist_id=anilist_id,
                romaji_title=anime_record.romaji_title,
                english_title=anime_record.english_title,
                native_title=anime_record.native_title,
                popularity=anime_record.popularity or 0,
                season=anime_record.season,
                season_year=anime_record.season_year,
                episodes=anime_record.episodes,
                format=anime_record.format,
                status=anime_record.status,
                small_cover_image=anime_record.small_cover_image,
                banner_image=anime_record.banner_image,
                user_list_status=user_entry.status if user_entry else None,
                tracked_anime_id=tracked_anime.id if tracked_anime else None,
                tracked_from_episode=tracked_anime.from_episode if tracked_anime else None
            ))

        return AiringScheduleListResponse(
            airing_schedule=sorted(airing_schedule_items, key=lambda item: (item.airing_at, item.anilist_id)),
            anime=anime_items,
        )
