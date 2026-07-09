from dataclasses import dataclass
from datetime import datetime, UTC, timedelta

from constants import AnilistAnimeSeason, AnilistAnimeStatus, AnilistAnimeUserStatus, AnilistTitleLanguage, \
    AnilistAnimeFormat, AnilistAnimeSource
from dto.orm_models import AnilistListItem, TrackedAnime
from utils.helpers.text_helpers import clean_text_with_html_tags


@dataclass(frozen=True)
class AnilistAiringScheduleItem:
    anilist_id: int | None
    episode: int | None
    airing_at: int | None

    @classmethod
    def from_dict(cls, data: dict) -> 'AnilistAiringScheduleItem':
        return cls(
            airing_at=data.get('airingAt'),
            episode=data.get('episode'),
            anilist_id=(data.get('media') or {}).get('id'),
        )


@dataclass
class AnilistDate:
    year: int | None
    month: int | None
    day: int | None

    @classmethod
    def from_dict(cls, data: dict | None) -> 'AnilistDate':
        if data is None:
            return cls(year=None, month=None, day=None)
        return cls(
            year=data.get('year'),
            month=data.get('month'),
            day=data.get('day')
        )

    def parsed_date(self, ceil_null=False, floor_null=False) -> datetime | None:
        if not self.year:
            return None
        if not self.month:
            if ceil_null:
                return datetime(self.year, 12, 31, tzinfo=UTC)
            if floor_null:
                return datetime(self.year, 1, 1, tzinfo=UTC)
            return None
        if not self.day:
            if ceil_null:
                if self.month == 12:
                    return datetime(self.year + 1, 1, 1, tzinfo=UTC)
                else:
                    return datetime(self.year, self.month + 1, 1, tzinfo=UTC)
            if floor_null:
                return datetime(self.year, self.month, 1, tzinfo=UTC)
            return None
        return datetime(self.year, self.month, self.day, tzinfo=UTC)


@dataclass
class AnilistTag:
    name: str
    rank: int
    is_media_spoiler: bool
    is_general_spoiler: bool

    @classmethod
    def from_dict(cls, data: dict) -> 'AnilistTag':
        return cls(
            name=data.get('name', ''),
            rank=data.get('rank', 0),
            is_media_spoiler=data.get('isMediaSpoiler', False),
            is_general_spoiler=data.get('isGeneralSpoiler', False)
        )

    @classmethod
    def many_from_dict(cls, data_list: list[dict] | None) -> list['AnilistTag']:
        if data_list is None:
            return []
        return [cls.from_dict(data) for data in data_list]


@dataclass
class AnilistStudio:
    name: str
    site_url: str
    is_primary: bool

    @classmethod
    def from_dict(cls, data: dict) -> 'AnilistStudio':
        return cls(
            name=data.get('node').get('name'),
            site_url=data.get('node').get('siteUrl'),
            is_primary=data.get('isMain')
        )

    @classmethod
    def many_from_dict(cls, data_list: list[dict] | None) -> list['AnilistStudio']:
        if data_list is None:
            return []
        return [cls.from_dict(data) for data in data_list]


@dataclass
class AnilistExternalLink:
    site: str | None
    url: str | None

    @classmethod
    def from_dict(cls, data: dict) -> 'AnilistExternalLink':
        return cls(
            site=data.get('site'),
            url=data.get('url')
        )

    @classmethod
    def many_from_dict(cls, data_list: list[dict] | None) -> list['AnilistExternalLink']:
        if data_list is None:
            return []
        return [cls.from_dict(data) for data in data_list]


@dataclass
class AnilistAnimeMinimal:
    _id: int
    _english_title: str | None
    _romaji_title: str | None
    _native_title: str | None
    expiry: datetime
    last_accessed: datetime

    @classmethod
    def from_dict(cls, data: dict) -> 'AnilistAnimeMinimal':
        return cls(
            _id=data['id'],
            _english_title=(data.get('title') or {}).get('english'),
            _romaji_title=(data.get('title') or {}).get('romaji'),
            _native_title=(data.get('title') or {}).get('native'),
            expiry=datetime.now(UTC) + timedelta(days=1),
            last_accessed=datetime.now(UTC)
        )

    @classmethod
    def from_anilist_anime(cls, anilist_anime: 'AnilistAnime') -> 'AnilistAnimeMinimal':
        return cls(
            _id=anilist_anime.id,
            _english_title=anilist_anime.english_title,
            _romaji_title=anilist_anime.romaji_title,
            _native_title=anilist_anime.native_title,
            expiry=datetime.now(UTC) + timedelta(days=1),
            last_accessed=datetime.now(UTC)
        )

    @classmethod
    def from_tracked_anime(cls, tracked_anime: TrackedAnime):
        return cls(
            _id=tracked_anime.anilist_id,
            _english_title=tracked_anime.english_title,
            _romaji_title=tracked_anime.romaji_title,
            _native_title=tracked_anime.native_title,
            expiry=datetime.now(UTC) + timedelta(days=1),
            last_accessed=datetime.now(UTC)
        )

    @property
    def id(self) -> int:
        self.last_accessed = datetime.now(UTC)
        return self._id

    @property
    def english_title(self) -> str:
        self.last_accessed = datetime.now(UTC)
        return self._english_title

    @property
    def romaji_title(self) -> str:
        self.last_accessed = datetime.now(UTC)
        return self._romaji_title

    @property
    def native_title(self) -> str:
        self.last_accessed = datetime.now(UTC)
        return self._native_title

    @id.setter
    def id(self, value):
        self._id = value

    @english_title.setter
    def english_title(self, value):
        self._english_title = value

    @romaji_title.setter
    def romaji_title(self, value):
        self._romaji_title = value

    @native_title.setter
    def native_title(self, value):
        self._native_title = value

    @property
    def expired(self) -> bool:
        return datetime.now(UTC) > self.expiry


@dataclass
class AnilistAnime:
    id: int
    idMal: int | None
    english_title: str | None
    romaji_title: str | None
    native_title: str | None
    description: str | None
    season: AnilistAnimeSeason | None
    season_year: int | None
    episodes: int | None
    duration: int | None
    source: AnilistAnimeSource | None
    status: AnilistAnimeStatus
    average_score: int | None
    mean_score: int | None
    popularity: int | None
    format: AnilistAnimeFormat | None
    country_of_origin: str | None
    hashtag: str | None
    synonyms: list[str]
    start_date: AnilistDate
    end_date: AnilistDate
    genres: list[str]
    tags: list[AnilistTag]
    is_adult: bool
    next_airing_episode: AnilistAiringScheduleItem | None
    studios: list[AnilistStudio]
    trailer_url: str | None
    banner_image: str | None
    small_cover_image: str | None
    medium_cover_image: str | None
    large_cover_image: str | None
    external_links: list[AnilistExternalLink]

    @classmethod
    def from_dict(cls, data: dict) -> 'AnilistAnime':
        youtube_trailer_url = ("https://www.youtube.com/watch?v=" + data["trailer"]["id"]) \
            if data.get('trailer') and data["trailer"].get('id') and data["trailer"].get('site') == 'youtube' else None
        next_airing_episode = AnilistAiringScheduleItem.from_dict(data['nextAiringEpisode']) \
            if data.get('nextAiringEpisode') else None
        return cls(
            id=data['id'],
            idMal=data.get('idMal'),
            english_title=(data.get('title') or {}).get('english'),
            romaji_title=(data.get('title') or {}).get('romaji'),
            native_title=(data.get('title') or {}).get('native'),
            description=data.get('description'),
            season=AnilistAnimeSeason(data['season']) if data.get('season') else None,
            season_year=data.get('seasonYear'),
            episodes=data.get('episodes'),
            duration=data.get('duration'),
            source=AnilistAnimeSource(data.get('source')) if data.get('source') else None,
            status=AnilistAnimeStatus(data['status']) if data.get('status') else AnilistAnimeStatus.NOT_YET_RELEASED,
            average_score=data.get('averageScore'),
            mean_score=data.get('meanScore'),
            popularity=data.get('popularity'),
            format=AnilistAnimeFormat(data.get('format')) if data.get('format') else None,
            country_of_origin=data.get('countryOfOrigin'),
            hashtag=data.get('hashtag'),
            synonyms=data.get('synonyms') or [],
            start_date=AnilistDate.from_dict(data.get('startDate')),
            end_date=AnilistDate.from_dict(data.get('endDate')),
            genres=data.get('genres', []),
            tags=AnilistTag.many_from_dict(data.get('tags')),
            is_adult=data.get('isAdult', False),
            next_airing_episode=next_airing_episode,
            studios=AnilistStudio.many_from_dict((data.get('studios') or {}).get('edges')),
            trailer_url=youtube_trailer_url,
            banner_image=data.get('bannerImage'),
            small_cover_image=(data.get('coverImage') or {}).get('medium'),
            medium_cover_image=(data.get('coverImage') or {}).get('large'),
            large_cover_image=(data.get('coverImage') or {}).get('extraLarge'),
            external_links=AnilistExternalLink.many_from_dict(data.get('externalLinks'))
        )

    @classmethod
    def many_from_dict(cls, data_list: list[dict]) -> list['AnilistAnime']:
        return [cls.from_dict(data) for data in data_list]

    @property
    def preferred_title(self) -> str:
        from config import config
        match config.user_settings.anilist_preferred_title_language:
            case AnilistTitleLanguage.ROMAJI:
                return self.romaji_title
            case AnilistTitleLanguage.NATIVE:
                return self.native_title or self.romaji_title
            case AnilistTitleLanguage.ENGLISH:
                return self.english_title or self.romaji_title
            case _:
                raise

    @property
    def clean_description(self) -> str | None:
        return clean_text_with_html_tags(self.description) if self.description else None


@dataclass
class AnilistUserListEntry:
    entry_id: int
    anime_id: int
    progress: int
    score: float
    status: AnilistAnimeUserStatus
    repeat_count: int
    is_private: bool
    started_at: AnilistDate
    completed_at: AnilistDate
    notes: str | None
    raw_data: dict

    @classmethod
    def from_dict(cls, data: dict) -> 'AnilistUserListEntry':
        return cls(
            entry_id=data['id'],
            anime_id=data['mediaId'],
            progress=data.get('progress', 0),
            score=data.get('score', 0.0),
            status=AnilistAnimeUserStatus(data['status']),
            repeat_count=data.get('repeat', 0),
            is_private=data.get('private', False),
            started_at=AnilistDate.from_dict(data.get('startedAt')),
            completed_at=AnilistDate.from_dict(data.get('completedAt')),
            notes=data.get('notes'),
            raw_data=data
        )

    def started_at_empty(self):
        return self.started_at.year is None and self.started_at.month is None and self.started_at.day is None

    def completed_at_empty(self):
        return self.completed_at.year is None and self.completed_at.month is None and self.completed_at.day is None


@dataclass
class AnilistUserList:
    all_entries_map: dict[int, AnilistUserListEntry]
    completed_anime_ids: set[int]
    planning_anime_ids: set[int]
    current_anime_ids: set[int]
    dropped_anime_ids: set[int]
    paused_anime_ids: set[int]

    @classmethod
    def from_list_of_orm(cls, anilist_list_items: list[AnilistListItem]) -> 'AnilistUserList':
        return cls.from_list_of_dict(data=[item.data for item in anilist_list_items])

    @classmethod
    def from_list_of_dict(cls, data: list[dict]) -> 'AnilistUserList':
        obj = cls(
            all_entries_map={},
            completed_anime_ids=set(),
            planning_anime_ids=set(),
            current_anime_ids=set(),
            dropped_anime_ids=set(),
            paused_anime_ids=set()
        )
        obj.set_user_list(data)
        return obj

    def set_user_list(self, data: list[dict]):
        self.all_entries_map.clear()
        self.completed_anime_ids.clear()
        self.planning_anime_ids.clear()
        self.current_anime_ids.clear()
        self.dropped_anime_ids.clear()
        self.paused_anime_ids.clear()
        for entry_data in data:
            anilist_entry = AnilistUserListEntry.from_dict(entry_data)
            self.all_entries_map[anilist_entry.anime_id] = anilist_entry
            self._add_anime_id_to_status_set(anilist_entry.anime_id, AnilistAnimeUserStatus(entry_data['status']))

    def _add_anime_id_to_status_set(self, anime_id: int, status: AnilistAnimeUserStatus):
        if status in [AnilistAnimeUserStatus.COMPLETED, AnilistAnimeUserStatus.REPEATING]:
            self.completed_anime_ids.add(anime_id)
        elif status == AnilistAnimeUserStatus.PLANNING:
            self.planning_anime_ids.add(anime_id)
        elif status == AnilistAnimeUserStatus.CURRENT:
            self.current_anime_ids.add(anime_id)
        elif status == AnilistAnimeUserStatus.DROPPED:
            self.dropped_anime_ids.add(anime_id)
        elif status == AnilistAnimeUserStatus.PAUSED:
            self.paused_anime_ids.add(anime_id)

    def get_entry_by_anime_id(self, anime_id: int) -> AnilistUserListEntry | None:
        return self.all_entries_map.get(anime_id)
