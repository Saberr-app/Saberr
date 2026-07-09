from app_state import anime_relations
from common.decorators import api_component
from common.exceptions import ExternalServiceException, NotFoundException
from components import BaseComponent
from components.service_components.anilist_list_component import AnilistListComponent
from components.service_components.anilist_component import AnilistComponent
from components.operational_components.tracked_anime_component import TrackedAnimeComponent
from components.service_components.anilist_airing_schedule_component import AnilistAiringScheduleComponent
from config import config
from constants import AnilistAnimeSeason, SortDirection, AnilistTitleLanguage, TrackedAnimeStatus
from dto.anilist import AnilistAnime, AnilistDate, AnilistUserListEntry, AnilistAiringScheduleItem
from api.schemas.anime_schemas import AnimeItem, AnimeItemBase, AnilistItemAiringScheduleItem
from api.schemas.user_anime_list_schemas import UserAnimeListRequest, UserAnimeListResponse, \
    UserAnimeUpdateRequest, UserAnimeUpdateResponse, UserAnimeListItem, UserAnimeBatchUpdateRequest, \
    UserAnimeBatchUpdateResponse, UserAnimeBatchDeleteRequest, UserAnimeListItemMinimal


class UserAnimeListAPIComponent(BaseComponent):

    def __init__(self):
        super().__init__()
        self._anilist_list_component = AnilistListComponent()
        self._anilist_component = AnilistComponent()
        self._tracked_anime_component = TrackedAnimeComponent()
        self._anilist_airing_schedule_component = AnilistAiringScheduleComponent()

    @api_component
    async def get_anime_list(self, params: UserAnimeListRequest) -> UserAnimeListResponse:
        user_list = await self._anilist_list_component.get_user_anime_list(force_fetch=params.force_freshness,
                                                                           fetch_full_anime_data=params.force_freshness)
        entries = list(user_list.all_entries_map.values())
        anime_id_anime_map = await self._hydrate_anime(entries)
        airing_schedules = await self._anilist_airing_schedule_component.get_future_anime_schedule_records_map(
            anilist_id_status_map={anime_id: anime.status for anime_id, anime in anime_id_anime_map.items()},
            force_fetch=params.force_freshness
        )
        tracked_anime = await self._tracked_anime_component.get_tracked_anime_by_anilist_ids(
            anilist_ids=list(anime_id_anime_map.keys()), load_relations=False
        )
        anilist_id_tracked_anime_id = {tracked.anilist_id: tracked.id for tracked in tracked_anime
                                       if tracked.status == TrackedAnimeStatus.ACTIVE}
        pairs = [(entry, anime_id_anime_map[entry.anime_id]) for entry in entries]
        pairs = self._filter(pairs, params, anilist_id_tracked_anime_id)
        pairs = self._sort(pairs, params.sort_by, params.sort_direction)
        page = pairs[params.offset:params.offset + params.limit]
        return UserAnimeListResponse(
            anime_list=[
                self._to_list_item(entry=entry,
                                   anime=anime,
                                   airing_schedule=airing_schedules.get(anime.id) or [],
                                   tracked_anime_id=anilist_id_tracked_anime_id.get(anime.id),
                                   tvdb_series_id=await anime_relations.get_anilist_id_tvdb_series_id(anime.id))
                for entry, anime in page
            ]
        )

    @api_component
    async def get_anime_list_entry(self, anilist_id: int, force_freshness: bool) -> UserAnimeListItem:
        user_list_entry = await self._anilist_list_component.get_user_anime_list_entry(anilist_id=anilist_id,
                                                                                       force_fetch=force_freshness)
        if not user_list_entry:
            raise NotFoundException(f"Anime list entry with anilist id {anilist_id} not found")
        anime = await self._anilist_component.get_anime(anilist_anime_id=anilist_id)
        airing_schedules = await self._anilist_airing_schedule_component.get_future_anime_schedule_records_map(
            anilist_id_status_map={anime.id: anime.status}, force_fetch=force_freshness
        )
        tracked_anime = await self._tracked_anime_component.get_tracked_anime(
            anilist_id=anilist_id, load_relations=False
        )
        return self._to_list_item(
            entry=user_list_entry,
            anime=anime,
            airing_schedule=airing_schedules.get(anime.id) or [],
            tracked_anime_id=tracked_anime.id
            if tracked_anime and tracked_anime.status == TrackedAnimeStatus.ACTIVE
            else None,
            tvdb_series_id=await anime_relations.get_anilist_id_tvdb_series_id(anime.id)
        )

    @api_component
    async def update_anime_list_entry(self, anilist_id: int,
                                      body: UserAnimeUpdateRequest) -> UserAnimeUpdateResponse:
        entry = await self._anilist_list_component.update_user_list_entry(
            anilist_anime_id=anilist_id,
            status=body.status,
            progress=body.progress,
            score=body.score,
            repeat_count=body.repeat_count,
            started_at=body.started_at,
            completed_at=body.completed_at,
            is_private=body.is_private,
            notes=body.notes,
        )
        anime_id_anime_map = await self._hydrate_anime([entry])
        airing_schedules = await self._anilist_airing_schedule_component.get_future_anime_schedule_records_map(
            anilist_id_status_map={anime_id: anime.status for anime_id, anime in anime_id_anime_map.items()},
        )
        tracked_anime = await self._tracked_anime_component.get_tracked_anime(
            anilist_id=anilist_id, load_relations=False
        )
        return UserAnimeUpdateResponse(
            **self._to_list_item(
                entry=entry,
                anime=anime_id_anime_map[anilist_id],
                airing_schedule=airing_schedules.get(anilist_id) or [],
                tracked_anime_id=tracked_anime.id
                if tracked_anime and tracked_anime.status == TrackedAnimeStatus.ACTIVE
                else None,
                tvdb_series_id=await anime_relations.get_anilist_id_tvdb_series_id(anilist_id)
            ).model_dump()
        )

    @api_component
    async def delete_anime_list_item(self, anilist_id: int) -> None:
        await self._anilist_list_component.delete_user_list_entry(anilist_anime_id=anilist_id)

    async def _hydrate_anime(self, entries: list[AnilistUserListEntry]) -> dict[int, AnilistAnime]:
        anime_ids = [entry.anime_id for entry in entries]
        anime_records = await self._anilist_component.get_anime_records(anilist_anime_ids=anime_ids)
        anime_id_anime_map = {anime.id: anime for anime in anime_records}
        missing_ids = set(anime_ids) - anime_id_anime_map.keys()
        if missing_ids:
            raise ExternalServiceException(f"Could not load anime metadata for ids: {sorted(missing_ids)}")
        return anime_id_anime_map

    @staticmethod
    def _filter(pairs: list[tuple[AnilistUserListEntry, AnilistAnime]],
                params: UserAnimeListRequest,
                anilist_id_tracked_anime_id: dict[int, int | None]) -> list[tuple[AnilistUserListEntry, AnilistAnime]]:
        result = pairs
        if params.query:
            query = params.query.lower()
            result = [(entry, anime) for entry, anime in result
                      if any(query in title.lower()
                             for title in [anime.english_title, anime.romaji_title, anime.native_title, *anime.synonyms]
                             if title)]
        if params.statuses:
            statuses = set(params.statuses)
            result = [(entry, anime) for entry, anime in result if entry.status in statuses]
        if params.airing_statuses:
            airing_statuses = set(params.airing_statuses)
            result = [(entry, anime) for entry, anime in result if anime.status in airing_statuses]
        if params.formats:
            formats = set(params.formats)
            result = [(entry, anime) for entry, anime in result if anime.format in formats]
        if params.season is not None:
            result = [(entry, anime) for entry, anime in result if anime.season == params.season]
        if params.season_year is not None:
            result = [(entry, anime) for entry, anime in result if anime.season_year == params.season_year]
        if params.is_tracked is not None:
            if params.is_tracked:
                result = [(entry, anime) for entry, anime in result if anilist_id_tracked_anime_id.get(anime.id)]
            else:
                result = [(entry, anime) for entry, anime in result if not anilist_id_tracked_anime_id.get(anime.id)]
        return result

    def _sort(self, pairs: list[tuple[AnilistUserListEntry, AnilistAnime]],
              sort_by: UserAnimeListRequest.UserAnimeListSortBy,
              sort_direction: SortDirection) -> list[tuple[AnilistUserListEntry, AnilistAnime]]:
        # sort by title first so it acts as a stable secondary tiebreak; entries whose sort value is
        # missing always go last, regardless of direction
        by_title = sorted(pairs, key=lambda pair: self._title_key(pair[1]))
        keyed = [(self._sort_value(entry, anime, sort_by), (entry, anime)) for entry, anime in by_title]
        present = [item for item in keyed if item[0] is not None]
        missing = [item for item in keyed if item[0] is None]
        present.sort(key=lambda item: item[0], reverse=sort_direction is SortDirection.DESC)
        return [pair for _, pair in present] + [pair for _, pair in missing]

    def _sort_value(self,
                    entry: AnilistUserListEntry,
                    anime: AnilistAnime,
                    sort_by: UserAnimeListRequest.UserAnimeListSortBy):
        match sort_by:
            case UserAnimeListRequest.UserAnimeListSortBy.TITLE:
                return self._title_key(anime)
            case UserAnimeListRequest.UserAnimeListSortBy.SEASON_AND_YEAR:
                if anime.season_year is None:
                    return None
                return anime.season_year, {AnilistAnimeSeason.WINTER: 0,
                                           AnilistAnimeSeason.SPRING: 1,
                                           AnilistAnimeSeason.SUMMER: 2,
                                           AnilistAnimeSeason.FALL: 3}.get(anime.season, -1)
            case UserAnimeListRequest.UserAnimeListSortBy.EPISODES:
                return anime.episodes
            case UserAnimeListRequest.UserAnimeListSortBy.STARTED_AT:
                return self._date_key(entry.started_at)
            case UserAnimeListRequest.UserAnimeListSortBy.COMPLETED_AT:
                return self._date_key(entry.completed_at)
            case UserAnimeListRequest.UserAnimeListSortBy.PROGRESS:
                return entry.progress
            case UserAnimeListRequest.UserAnimeListSortBy.SCORE:
                return entry.score
            case UserAnimeListRequest.UserAnimeListSortBy.STATUS:
                return entry.status.value
            case UserAnimeListRequest.UserAnimeListSortBy.FORMAT:
                return anime.format.value if anime.format else None
            case UserAnimeListRequest.UserAnimeListSortBy.SOURCE:
                return anime.source.value if anime.source else None
            case UserAnimeListRequest.UserAnimeListSortBy.AIRING_STATUS:
                return anime.status.value if anime.status else None
            case UserAnimeListRequest.UserAnimeListSortBy.REPEAT_COUNT:
                return entry.repeat_count
            case UserAnimeListRequest.UserAnimeListSortBy.TIME_UNTIL_AIRING:
                return anime.next_airing_episode.airing_at if anime.next_airing_episode else None
            case _:
                return None

    @staticmethod
    def _title_key(anime: AnilistAnime) -> str:
        match config.user_settings.anilist_preferred_title_language:
            case AnilistTitleLanguage.ROMAJI:
                return anime.romaji_title
            case AnilistTitleLanguage.ENGLISH:
                return anime.english_title or anime.romaji_title
            case AnilistTitleLanguage.NATIVE:
                return anime.native_title or anime.romaji_title
            case _:
                raise

    @staticmethod
    def _date_key(date: AnilistDate) -> tuple[int, int, int] | None:
        if date.year is None:
            return None
        return date.year, date.month or 0, date.day or 0

    def _to_list_item(self, entry: AnilistUserListEntry,
                      anime: AnilistAnime,
                      airing_schedule: list[AnilistAiringScheduleItem],
                      tvdb_series_id: int | None,
                      tracked_anime_id: int | None) -> UserAnimeListItem:
        return UserAnimeListItem(
            anime=self._to_anime_item(anime=anime, airing_schedule=airing_schedule, tvdb_series_id=tvdb_series_id),
            progress=entry.progress,
            score=entry.score,
            status=entry.status,
            repeat_count=entry.repeat_count,
            is_private=entry.is_private,
            started_at=AnimeItem.AnilistDate(year=entry.started_at.year,
                                             month=entry.started_at.month,
                                             day=entry.started_at.day),
            completed_at=AnimeItem.AnilistDate(year=entry.completed_at.year,
                                               month=entry.completed_at.month,
                                               day=entry.completed_at.day),
            notes=entry.notes,
            tracked_anime_id=tracked_anime_id
        )

    @staticmethod
    def _to_anime_item(anime: AnilistAnime,
                       airing_schedule: list[AnilistAiringScheduleItem],
                       tvdb_series_id: int | None) -> AnimeItemBase:
        next_airing_episode = None
        if airing_schedule:
            next_airing_episode = sorted(airing_schedule, key=lambda x: x.airing_at)[0]
            next_airing_episode = AnilistItemAiringScheduleItem(
                airing_at=next_airing_episode.airing_at,
                episode=next_airing_episode.episode,
                anilist_id=next_airing_episode.anilist_id,
            )
        return AnimeItemBase(
            id=anime.id,
            idMal=anime.idMal,
            tvdb_series_id=tvdb_series_id,
            english_title=anime.english_title,
            romaji_title=anime.romaji_title,
            native_title=anime.native_title,
            season=anime.season,
            season_year=anime.season_year,
            episodes=anime.episodes,
            status=anime.status,
            average_score=anime.average_score,
            mean_score=anime.mean_score,
            next_airing_episode=next_airing_episode,
            banner_image=anime.banner_image,
            small_cover_image=anime.small_cover_image,
            medium_cover_image=anime.medium_cover_image,
            large_cover_image=anime.large_cover_image,
            format=anime.format,
            start_date=AnimeItemBase.AnilistDate(
                year=anime.start_date.year,
                month=anime.start_date.month,
                day=anime.start_date.day,
            ),
            end_date=AnimeItemBase.AnilistDate(
                year=anime.end_date.year,
                month=anime.end_date.month,
                day=anime.end_date.day,
            )
        )

    async def batch_update_anime_list_entries(self, body: UserAnimeBatchUpdateRequest) -> UserAnimeBatchUpdateResponse:
        list_entries = await self._anilist_list_component.update_user_list_entries(anilist_ids=body.anilist_ids,
                                                                                   status=body.data.status,
                                                                                   score=body.data.score)
        tracked_anime_list = await self._tracked_anime_component.get_tracked_anime_by_anilist_ids(
            anilist_ids=body.anilist_ids, load_relations=False
        )
        anilist_id_tracked_anime_id_map = {tracked_anime.anilist_id: tracked_anime.id
                                           for tracked_anime in tracked_anime_list}
        items = [UserAnimeListItemMinimal(
            progress=list_entry.progress,
            score=list_entry.score,
            status=list_entry.status,
            repeat_count=list_entry.repeat_count,
            is_private=list_entry.is_private,
            started_at=AnimeItem.AnilistDate(year=list_entry.started_at.year,
                                             month=list_entry.started_at.month,
                                             day=list_entry.started_at.day),
            completed_at=AnimeItem.AnilistDate(year=list_entry.completed_at.year,
                                               month=list_entry.completed_at.month,
                                               day=list_entry.completed_at.day),
            notes=list_entry.notes,
            tracked_anime_id=anilist_id_tracked_anime_id_map.get(list_entry.anime_id),
            anilist_id=list_entry.anime_id
        ) for list_entry in list_entries]
        return UserAnimeBatchUpdateResponse(updated_anime_list=items)

    async def batch_delete_anime_list_entries(self, body: UserAnimeBatchDeleteRequest):
        await self._anilist_list_component.delete_user_list_entries(anilist_ids=body.anilist_ids)
