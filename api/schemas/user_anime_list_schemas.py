from enum import Enum

from pydantic import BaseModel

from api.schemas import NonEmptyString, bounded_list
from constants import SortDirection, AnilistAnimeUserStatus, AnilistAnimeSeason, AnilistAnimeStatus, AnilistAnimeFormat
from api.schemas.anime_schemas import AnimeItem, AnimeItemBase


class UserAnimeListRequest(BaseModel):
    
    class UserAnimeListSortBy(Enum):
        TITLE = 'title'
        SEASON_AND_YEAR = 'season_and_year'
        EPISODES = 'episodes'
        STARTED_AT = 'started_at'
        COMPLETED_AT = 'completed_at'
        PROGRESS = 'progress'
        SCORE = 'score'
        STATUS = 'status'
        FORMAT = 'format'
        SOURCE = 'source'
        AIRING_STATUS = 'airing_status'
        REPEAT_COUNT = 'repeat_count'
        TIME_UNTIL_AIRING = 'time_until_airing'

    query: str | None = None  # any of the 3 titles, synonyms
    statuses: list[AnilistAnimeUserStatus] = []
    season: AnilistAnimeSeason | None = None
    season_year: int | None = None
    is_tracked: bool | None = None
    airing_statuses: list[AnilistAnimeStatus] = []
    formats: list[AnilistAnimeFormat] = []
    sort_direction: SortDirection = SortDirection.DESC
    sort_by: UserAnimeListSortBy = UserAnimeListSortBy.SEASON_AND_YEAR
    offset: int = 0
    limit: int = 100
    force_freshness: bool = False


class UserAnimeListItem(BaseModel):
    progress: int
    score: float | int
    status: AnilistAnimeUserStatus
    repeat_count: int
    is_private: bool
    started_at: AnimeItem.AnilistDate
    completed_at: AnimeItem.AnilistDate
    notes: str | None
    anime: AnimeItemBase
    tracked_anime_id: int | None


class UserAnimeListItemMinimal(UserAnimeListItem):
    anime: None = None
    anilist_id: int
    pass


class UserAnimeListResponse(BaseModel):
    anime_list: list[UserAnimeListItem]


class UserAnimeUpdateRequest(BaseModel):
    progress: int
    score: float | int
    status: AnilistAnimeUserStatus
    repeat_count: int
    is_private: bool
    started_at: AnimeItem.AnilistDate
    completed_at: AnimeItem.AnilistDate
    notes: NonEmptyString | None


class UserAnimeUpdateResponse(UserAnimeListItem):
    pass


class UserAnimeBatchUpdateRequestData(BaseModel):
    score: float | int = None
    status: AnilistAnimeUserStatus = None


class UserAnimeBatchUpdateRequest(BaseModel):
    anilist_ids: bounded_list(int, min_len=1, max_len=25)
    data: UserAnimeBatchUpdateRequestData


class UserAnimeBatchUpdateResponse(BaseModel):
    updated_anime_list: list[UserAnimeListItemMinimal]


class UserAnimeBatchDeleteRequest(BaseModel):
    anilist_ids: bounded_list(int, min_len=1, max_len=50)
