from datetime import datetime

from pydantic import BaseModel

from api.schemas import cached_asset
from constants import MappingOverrideMode


class MappingOverrideRequest(BaseModel):
    anilist_id: int
    anilist_episode_number_from: int
    anilist_episode_number_to: int | None
    tvdb_series_id: int
    tvdb_season_number: int
    tvdb_episode_number_from: int
    tvdb_episode_number_to: int | None
    granularity: int
    mode: MappingOverrideMode


class MappingOverrideItem(MappingOverrideRequest):
    id: int
    anilist_english_title: str | None
    anilist_native_title: str | None
    anilist_romaji_title: str
    anilist_small_cover_image: cached_asset()
    tvdb_title: str
    tvdb_image_url: cached_asset()


class MappingOverrideListResponse(BaseModel):
    mapping_overrides: list[MappingOverrideItem]


class MappingStatsResponse(BaseModel):
    anime_relations_count: int
    anilist_tvdb_mappings_count: int
    anime_relations_last_updated_at: datetime
    anilist_tvdb_mappings_last_updated_at: datetime
