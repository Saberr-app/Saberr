from enum import Enum
from typing import Literal

from pydantic import BaseModel

from api.schemas import cached_asset
from constants import AnilistAnimeSeason, AnilistAnimeStatus, AnilistAnimeFormat, AnilistAnimeSource, \
    AnilistAnimeUserStatus, AnilistFormat, MetadataSource


class AnimeListRequest(BaseModel):

    class AnimeSortBy(Enum):
        ID = "ID"
        TITLE_ROMAJI = "TITLE_ROMAJI"
        TITLE_ROMAJI_DESC = "TITLE_ROMAJI_DESC"
        TITLE_ENGLISH = "TITLE_ENGLISH"
        TITLE_ENGLISH_DESC = "TITLE_ENGLISH_DESC"
        TITLE_NATIVE = "TITLE_NATIVE"
        TITLE_NATIVE_DESC = "TITLE_NATIVE_DESC"
        TYPE = "TYPE"
        TYPE_DESC = "TYPE_DESC"
        FORMAT = "FORMAT"
        FORMAT_DESC = "FORMAT_DESC"
        START_DATE = "START_DATE"
        START_DATE_DESC = "START_DATE_DESC"
        END_DATE = "END_DATE"
        END_DATE_DESC = "END_DATE_DESC"
        SCORE = "SCORE"
        SCORE_DESC = "SCORE_DESC"
        POPULARITY = "POPULARITY"
        POPULARITY_DESC = "POPULARITY_DESC"
        TRENDING = "TRENDING"
        TRENDING_DESC = "TRENDING_DESC"
        EPISODES = "EPISODES"
        EPISODES_DESC = "EPISODES_DESC"
        DURATION = "DURATION"
        DURATION_DESC = "DURATION_DESC"
        STATUS = "STATUS"
        STATUS_DESC = "STATUS_DESC"
        UPDATED_AT = "UPDATED_AT"
        UPDATED_AT_DESC = "UPDATED_AT_DESC"
        FAVOURITES = "FAVOURITES"
        FAVOURITES_DESC = "FAVOURITES_DESC"
        SEARCH_MATCH = "SEARCH_MATCH"

    query: str | None = None
    statuses: list[AnilistAnimeStatus] = []
    season: AnilistAnimeSeason | None = None
    season_year: int | None = None
    formats: list[AnilistAnimeFormat] = []
    sources: list[AnilistAnimeSource] = []
    genres: list[str] = []
    tags: list[str] = []
    exclude_genres: list[str] = []
    exclude_tags: list[str] = []
    on_list: bool | None = None
    sort_by: list[AnimeSortBy] = [AnimeSortBy.TRENDING_DESC]
    page: int = 1
    force_freshness: bool = False


class AnilistItemAiringScheduleItem(BaseModel):
    airing_at: int | None
    episode: int | None
    anilist_id: int | None


class AnimeItemBase(BaseModel):

    class AnilistDate(BaseModel):
        year: int | None
        month: int | None
        day: int | None

    id: int
    idMal: int | None
    tvdb_series_id: int | None
    english_title: str | None
    romaji_title: str | None
    native_title: str | None
    season: AnilistAnimeSeason | None
    season_year: int | None
    episodes: int | None
    status: AnilistAnimeStatus
    average_score: int | None
    mean_score: int | None
    next_airing_episode: AnilistItemAiringScheduleItem | None
    banner_image: cached_asset()
    small_cover_image: cached_asset()
    medium_cover_image: cached_asset()
    large_cover_image: cached_asset()
    format: AnilistAnimeFormat | None
    start_date: AnilistDate
    end_date: AnilistDate


class AnimeItem(AnimeItemBase):

    class AnilistTag(BaseModel):
        name: str
        rank: int
        is_media_spoiler: bool
        is_general_spoiler: bool

    class AnilistStudio(BaseModel):
        name: str
        site_url: str
        is_primary: bool

    class AnilistExternalLink(BaseModel):
        site: str | None
        url: str

    description: str | None
    source: AnilistAnimeSource | None
    popularity: int | None
    duration: int | None
    country_of_origin: str | None
    hashtag: str | None
    synonyms: list[str]
    genres: list[str]
    tags: list[AnilistTag]
    is_adult: bool
    studios: list[AnilistStudio]
    trailer_url: str | None
    external_links: list[AnilistExternalLink]


class AnimeItemWithUserEntry(AnimeItem):

    class UserEntry(BaseModel):
        progress: int
        score: float | int
        status: AnilistAnimeUserStatus
        repeat_count: int
        is_private: bool
        started_at: AnimeItem.AnilistDate
        completed_at: AnimeItem.AnilistDate
        notes: str | None

    user_entry: UserEntry | None
    tracked_anime_id: int | None


class AnimeListResponse(BaseModel):
    anime: list[AnimeItemWithUserEntry]


class AnilistMetadataResponse(BaseModel):

    class AnilistMetadataTag(BaseModel):
        name: str
        category: str

    tags: list[AnilistMetadataTag]
    genres: list[str]


class AnimeExtras(BaseModel):

    class Character(BaseModel):

        class CharacterStaff(BaseModel):
            site_url: str
            image_url: cached_asset()
            name: str

        site_url: str
        image_url: cached_asset()
        name: str
        role: Literal["MAIN", "SUPPORTING", "BACKGROUND"] | None
        voice_actor: CharacterStaff | None

    class Relation(BaseModel):
        id: int
        image_url: cached_asset()
        english_title: str | None
        romaji_title: str | None
        native_title: str | None
        format: AnilistFormat | None
        relation_type: Literal["ADAPTATION", "PREQUEL", "SEQUEL", "PARENT", "SIDE_STORY", "CHARACTER",
                               "SUMMARY", "ALTERNATIVE", "SPIN_OFF", "OTHER", "SOURCE", "COMPILATION", "CONTAINS"]
        list_status: AnilistAnimeUserStatus | None

    class Staff(BaseModel):
        site_url: str
        image_url: cached_asset()
        name: str
        role: str | None

    characters: list[Character]
    relations: list[Relation]
    staff: list[Staff]


class AnimeTitlesResponse(BaseModel):
    class Title(BaseModel):
        source: MetadataSource
        title: str
        language: str

    titles: list[Title]
