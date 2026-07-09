from pydantic import BaseModel

from api.schemas import cached_asset
from constants import AnilistAnimeFormat, AnilistAnimeSeason, AnilistAnimeStatus


class SearchRequest(BaseModel):
    query: str


class SearchResponse(BaseModel):
    class AnimeResult(BaseModel):
        anilist_id: int
        english_title: str | None
        native_title: str | None
        romaji_title: str
        episodes: int | None
        format: AnilistAnimeFormat | None
        season: AnilistAnimeSeason | None
        season_year: int | None
        status: AnilistAnimeStatus | None
        small_cover_image: cached_asset()
        user_list_status: str | None
        tracked_anime_id: int | None

    anime: list[AnimeResult]


class SearchTVDBResponse(BaseModel):
    class TVDBSeriesResult(BaseModel):
        id: int
        title: str
        year: int | None
        image_url: cached_asset()
        status: str | None

    tvdb_series: list[TVDBSeriesResult]
