from dataclasses import dataclass
from datetime import datetime

from constants import TVDBFinaleType, TVDBSeasonType
from dto.orm_models import TrackedAnimeEpisode


@dataclass
class TVDBSeriesEpisode:
    id: int
    series_id: int  # [seriesId]
    title: str | None  # [name]
    air_date: datetime | None  # [aired]
    runtime: int | None  # in minutes
    overview: str | None
    image_url: str | None  # [image]
    number: int | None  # should never be null
    absolute_number: int | None  # [absoluteNumber] should never be null
    season_number: int | None  # [seasonNumber] should never be null
    season_name: str | None  # [seasonName]
    finale_type: TVDBFinaleType | None  # [finaleType]
    season_type: TVDBSeasonType

    @classmethod
    def from_dict(cls, data: dict, season_type: TVDBSeasonType) -> 'TVDBSeriesEpisode':
        try:
            air_date = datetime.strptime(data["aired"], "%Y-%m-%d") if data.get("aired") else None
        except:
            air_date = None
        return cls(
            id=data["id"],
            series_id=data["seriesId"],
            title=data.get("name"),
            air_date=air_date,
            runtime=data.get("runtime"),
            overview=data.get("overview"),
            image_url=f"https://artworks.thetvdb.com{data['image']}" if data.get("image") else None,
            number=data.get("number"),
            absolute_number=data.get("absoluteNumber"),
            season_number=data.get("seasonNumber"),
            season_name=data.get("seasonName"),
            finale_type=TVDBFinaleType(data["finaleType"]) if data.get("finaleType") else None,
            season_type=season_type,
        )

    @classmethod
    def many_from_dict(cls, data_list: list[dict], season_type: TVDBSeasonType) -> list['TVDBSeriesEpisode']:
        return [cls.from_dict(data, season_type) for data in data_list]


@dataclass
class TVDBSeriesEpisodes:
    series_id: int
    season_type: TVDBSeasonType
    episodes: list[TVDBSeriesEpisode]

    @classmethod
    def from_episode_list(cls, series_id: int,
                          season_type: TVDBSeasonType,
                          episodes: list[dict]) -> 'TVDBSeriesEpisodes':
        return cls(
            series_id=series_id,
            season_type=season_type,
            episodes=TVDBSeriesEpisode.many_from_dict(episodes, season_type),
        )


@dataclass
class TVDBSeriesSearchResult:
    id: int  # [tvdb_id]
    original_name: str  # [name]
    original_overview: str | None  # [overview]
    english_name: str | None  # [translations][eng]
    english_overview: str | None  # [overviews][eng]
    aliases: list[str]  # [aliases]
    year: int | None  # int([year])
    status: str | None  # [status]
    image_url: str | None  # [image_url]
    thumbnail_url: str | None  # [thumbnail]

    @classmethod
    def from_dict(cls, data: dict) -> 'TVDBSeriesSearchResult':
        return cls(
            id=data["tvdb_id"],
            original_name=data["name"],
            original_overview=data.get("overview"),
            english_name=(data.get("translations") or {}).get("eng"),
            english_overview=(data.get("overviews") or {}).get("eng"),
            aliases=data.get("aliases") or [],
            year=int(data["year"]) if data.get("year") else None,
            status=data.get("status"),
            image_url=data.get("image_url"),
            thumbnail_url=data.get("thumbnail"),
        )

    @classmethod
    def many_from_dict(cls, data_list: list[dict]) -> list['TVDBSeriesSearchResult']:
        return [cls.from_dict(data) for data in data_list]


@dataclass
class TVDBSeriesAlias:
    title: str
    language: str


@dataclass
class TVDBSeries:
    title: str  # [name]
    english_title: str | None  # [eng_translation][name]
    aliases: list[TVDBSeriesAlias]
    overview: str | None  # [overview]
    english_overview: str | None  # [eng_translation][overview]
    image_url: str | None  # [image]
    year: int | None  # int([year])
    status: str  # [status][name]
    first_aired: datetime | None  # [firstAired] YYYY-MM-DD
    last_aired: datetime | None  # [lastAired] YYYY-MM-DD
    next_aired: datetime | None  # [nextAired] YYYY-MM-DD
    average_runtime: int | None  # [averageRuntime]
    official_seasons: list[int]

    @classmethod
    def from_dict(cls, data: dict) -> 'TVDBSeries':
        def parse_date(value):
            try:
                return datetime.strptime(value, "%Y-%m-%d") if value else None
            except:
                return None
        eng = data.get("eng_translation") or {}
        return cls(
            title=data["name"],
            english_title=eng.get("name"),
            aliases=[
                TVDBSeriesAlias(title=alias["name"], language=alias["language"])
                for alias in (data.get("aliases") or [])
            ],
            overview=data.get("overview"),
            english_overview=eng.get("overview"),
            image_url=data.get("image"),
            year=int(data["year"])
            if data.get("year") and isinstance(data["year"], str) and data["year"].isdigit() else None,
            status=(data.get("status") or {}).get("name"),
            first_aired=parse_date(data.get("firstAired")),
            last_aired=parse_date(data.get("lastAired")),
            next_aired=parse_date(data.get("nextAired")),
            average_runtime=data.get("averageRuntime"),
            official_seasons=[season["number"] for season in (data.get("seasons") or [])
                              if season["type"]["type"] == TVDBSeasonType.OFFICIAL.value]
        )


@dataclass
class AnilistEpisodeTVDBMapping:
    series_id: int
    season_number: int
    episode_number: int
    part: int | None  # only set if this anilist episode is only one part of a TVDB episode
    part_ceiling: int | None = None  # total number of parts when `part` is set, e.g. part 3 of 4 -> part_ceiling=4

    episode_id: int = None

    @classmethod
    def from_tracked_anime_episode(cls,
                                   tracked_anime_episode: TrackedAnimeEpisode) -> list['AnilistEpisodeTVDBMapping']:
        if not tracked_anime_episode.tvdb_episode_ids:
            return []
        mappings = []
        for i in range(len(tracked_anime_episode.tvdb_episode_ids)):  # noqa
            mapping = cls(
                series_id=tracked_anime_episode.tvdb_series_id,
                season_number=tracked_anime_episode.tvdb_season_number,
                episode_number=tracked_anime_episode.tvdb_episode_numbers[i],
                part=tracked_anime_episode.tvdb_episode_part,
                episode_id=tracked_anime_episode.tvdb_episode_ids[i],
            )
            mappings.append(mapping)
        return mappings


@dataclass
class TVDBEpisodeAnilistMapping:
    anilist_id: int
    episode_number: int
    part: int | None  # only set if this TVDB episode is only one part of an anilist episode
    part_ceiling: int | None = None  # total number of parts when `part` is set, e.g. part 3 of 4 -> part_ceiling=4
