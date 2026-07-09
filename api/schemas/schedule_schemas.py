from datetime import datetime

from pydantic import BaseModel

from api.schemas import cached_asset
from constants import AiringScheduleScope, TorrentDownloadStatus, AnilistAnimeUserStatus, AnilistAnimeStatus, \
    AnilistAnimeSeason, AnilistAnimeFormat


class AiringScheduleListRequest(BaseModel):
    month: datetime = None
    week: datetime = None
    day: datetime = None
    scope: list[AiringScheduleScope]
    force_refresh: bool = False


class AiringScheduleItem(BaseModel):
    id: int
    anilist_id: int
    airing_at: int
    episode: int
    title: str | None = None
    download_status: TorrentDownloadStatus | None


class AiringScheduleListResponse(BaseModel):

    class AnimeItem(BaseModel):
        anilist_id: int
        romaji_title: str
        english_title: str | None
        native_title: str | None
        popularity: int
        season: AnilistAnimeSeason | None
        season_year: int | None
        episodes: int | None
        format: AnilistAnimeFormat | None
        status: AnilistAnimeStatus
        small_cover_image: cached_asset()
        banner_image: cached_asset()
        user_list_status: AnilistAnimeUserStatus | None
        tracked_anime_id: int | None
        tracked_from_episode: int | None

    airing_schedule: list[AiringScheduleItem]
    anime: list[AnimeItem]
