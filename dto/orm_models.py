import json
from datetime import datetime, UTC

from sqlalchemy import TypeDecorator, ForeignKey, Computed
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from sqlalchemy.types import String, DateTime, JSON

from constants import (SettingsCode, TrackedAnimeStatus, TVDBSeasonType, TorrentDownloadStatus,
                       NotificationLevel, NotificationStatus, NotificationCode, AuditLogCode, AuditLogCategory,
                       Encoding, Resolution, VideoSource, CachedAssetRemoteType, Enum, ReleaseCriteriaProperty,
                       AnilistTitleLanguage, CachedAssetType, MappingOverrideMode)


class AwareDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive date-times not allowed")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


class Dynamic(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if isinstance(value, (dict, list, tuple, int, float, bool)):
            value = json.dumps(value)
        elif isinstance(value, Enum):
            value = value.value
        return value

    def process_result_value(self, value, dialect):
        try:
            value = json.loads(value)  # can handle bare int and float apparently, even bool...
        except (json.JSONDecodeError, TypeError):
            pass  # str or null
        return value


class EnumList(TypeDecorator):
    impl = JSON
    cache_ok = True

    def __init__(self, enum_cls: type[Enum], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._enum_cls = enum_cls

    @classmethod
    def __class_getitem__(cls, enum_cls: type[Enum]):
        return cls(enum_cls)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        # JSON impl serializes the returned list; we only convert enums to their values.
        return [item.value if isinstance(item, self._enum_cls) else item for item in value]

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return [self._enum_cls(item) for item in value]


class BaseModel(DeclarativeBase):
    pass


class BaseModelMixin:
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(AwareDateTime(),  # type: ignore[arg-type]
                                                 default=lambda: datetime.now(UTC),
                                                 nullable=False)
    updated_at: Mapped[datetime] = mapped_column(AwareDateTime(),  # type: ignore[arg-type]
                                                 default=lambda: datetime.now(UTC),
                                                 onupdate=lambda: datetime.now(UTC),
                                                 nullable=False)


class AnilistAnime(BaseModel, BaseModelMixin):
    __tablename__ = 'anilist_anime'

    anilist_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    data: Mapped[dict] = mapped_column(JSON(none_as_null=True), nullable=False)  # type: ignore[arg-type]
    search_blob: Mapped[str | None] = mapped_column(Computed('', persisted=True))  # type: ignore[arg-type]


class AnilistAnimeExtras(BaseModel, BaseModelMixin):
    __tablename__ = 'anilist_anime_extras'

    anilist_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    data: Mapped[dict] = mapped_column(JSON(none_as_null=True), nullable=False)  # type: ignore[arg-type]


class AnilistAnimeAiringSchedule(BaseModel, BaseModelMixin):
    __tablename__ = 'anilist_anime_airing_schedule'

    anilist_id: Mapped[int] = mapped_column(nullable=False)
    episode: Mapped[int] = mapped_column(nullable=False)
    airing_at: Mapped[int] = mapped_column(nullable=False)


class AnilistAnimeMonthlyAiringSchedule(BaseModel, BaseModelMixin):
    __tablename__ = 'anilist_anime_monthly_airing_schedule'

    anilist_id: Mapped[int] = mapped_column(nullable=False)
    month: Mapped[datetime] = mapped_column(AwareDateTime(), nullable=False)  # type: ignore[arg-type]
    data: Mapped[list] = mapped_column(JSON(none_as_null=True), nullable=False)  # type: ignore[arg-type]


class TVDBSeriesEpisodes(BaseModel, BaseModelMixin):
    __tablename__ = 'tvdb_series_episodes'

    tvdb_series_id: Mapped[int] = mapped_column(nullable=False)
    season_type: Mapped[TVDBSeasonType] = mapped_column(TVDBSeasonType.as_orm_enum(), nullable=False)
    data: Mapped[dict] = mapped_column(JSON(none_as_null=True), nullable=False)  # type: ignore[arg-type]


class TVDBSeries(BaseModel, BaseModelMixin):
    __tablename__ = 'tvdb_series'

    tvdb_series_id: Mapped[int] = mapped_column(nullable=False)
    data: Mapped[dict] = mapped_column(JSON(none_as_null=True), nullable=False)  # type: ignore[arg-type]


class AnilistListItem(BaseModel, BaseModelMixin):
    __tablename__ = 'anilist_list_item'

    anilist_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    data: Mapped[dict] = mapped_column(JSON(none_as_null=True), nullable=False)  # type: ignore[arg-type]


class Settings(BaseModel, BaseModelMixin):
    __tablename__ = 'settings'

    code: Mapped[SettingsCode] = mapped_column(SettingsCode.as_orm_enum(), unique=True, nullable=False)
    data: Mapped[Dynamic | None] = mapped_column(Dynamic(), nullable=True)  # type: ignore[arg-type]


class TrackedAnimeProfile(BaseModel, BaseModelMixin):
    __tablename__ = 'tracked_anime_profile'

    preferred_release_groups: Mapped[list] = mapped_column(JSON(none_as_null=True),  # type: ignore[arg-type]
                                                           nullable=False)
    preferred_encodings: Mapped[list[Encoding]] = mapped_column(EnumList[Encoding],  # type: ignore[arg-type]
                                                                nullable=False)
    preferred_resolutions: Mapped[list[Resolution]] = mapped_column(EnumList[Resolution],  # type: ignore[arg-type]
                                                                    nullable=False)
    preferred_language_codes: Mapped[list] = mapped_column(JSON(none_as_null=True),  # type: ignore[arg-type]
                                                           nullable=False)
    preferred_sources: Mapped[list[VideoSource]] = mapped_column(EnumList[VideoSource],  # type: ignore[arg-type]
                                                                 nullable=False)
    language_codes_restricted: Mapped[bool] = mapped_column(nullable=False, default=False)
    sources_restricted: Mapped[bool] = mapped_column(nullable=False, default=False)
    accept_release_upgrades: Mapped[bool] = mapped_column(nullable=False, default=True)
    priorities_sorted: Mapped[list[ReleaseCriteriaProperty]] = \
        mapped_column(EnumList[ReleaseCriteriaProperty], nullable=False)  # type: ignore[arg-type]

    tracked_anime_list: Mapped[list["TrackedAnime"]] = relationship(
        'TrackedAnime',
        back_populates='profile',
        uselist=True,
        cascade="save-update, merge, expunge"
    )


class TrackedAnime(BaseModel, BaseModelMixin):
    __tablename__ = 'tracked_anime'

    tracked_anime_profile_id: Mapped[int | None] = (
        mapped_column(ForeignKey("tracked_anime_profile.id"),  # type: ignore[arg-type]
                      nullable=False, default=1)
    )
    romaji_title: Mapped[str] = mapped_column(nullable=False)
    native_title: Mapped[str | None] = mapped_column(nullable=True)
    english_title: Mapped[str | None] = mapped_column(nullable=True)
    anilist_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    status: Mapped[TrackedAnimeStatus] = mapped_column(TrackedAnimeStatus.as_orm_enum(), nullable=False)
    from_episode: Mapped[int] = mapped_column(nullable=False, default=1)
    tvdb_structure_enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    tvdb_season_type: Mapped[TVDBSeasonType] = mapped_column(TVDBSeasonType.as_orm_enum(),
                                                             nullable=False,
                                                             default=TVDBSeasonType.OFFICIAL)
    show_parent_directory: Mapped[str] = mapped_column(nullable=False)
    show_folder_name: Mapped[str] = mapped_column(nullable=False)

    processing_settings: Mapped["TrackedAnimeProcessingSettings"] = relationship(
        'TrackedAnimeProcessingSettings',
        back_populates='tracked_anime',
        uselist=False,
        cascade="save-update, merge, expunge"
    )
    profile: Mapped["TrackedAnimeProfile"] = relationship(
        'TrackedAnimeProfile',
        back_populates='tracked_anime_list',
        uselist=False,
        cascade="save-update, merge, expunge"
    )
    release_groups_preferences: Mapped[list["TrackedAnimeReleaseGroupPreferences"]] = relationship(
        'TrackedAnimeReleaseGroupPreferences',
        back_populates='tracked_anime',
        uselist=True,
        cascade="save-update, merge, expunge"
    )
    episodes: Mapped[list["TrackedAnimeEpisode"]] = relationship(
        'TrackedAnimeEpisode',
        back_populates='tracked_anime',
        uselist=True,
        cascade="save-update, merge, expunge"
    )

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


class TrackedAnimeProcessingSettings(BaseModel, BaseModelMixin):
    __tablename__ = 'tracked_anime_processing_settings'

    tracked_anime_id: Mapped[int] = mapped_column(ForeignKey("tracked_anime.id"),  # type: ignore[arg-type]
                                                  nullable=False, unique=True)
    episode_number_padding: Mapped[int] = mapped_column(nullable=False, default=2)
    season_number_padding: Mapped[int] = mapped_column(nullable=False, default=2)
    season_directory_number_padding: Mapped[int] = mapped_column(nullable=False, default=1)
    season_directory_name_format: Mapped[str] = mapped_column(nullable=False)
    raw_episode_file_name_format: Mapped[str] = mapped_column(nullable=False)
    episode_file_name_format: Mapped[str] = mapped_column(nullable=False)
    titleless_episode_file_name_format: Mapped[str] = mapped_column(nullable=False)

    tracked_anime: Mapped["TrackedAnime"] = relationship(
        'TrackedAnime',
        back_populates='processing_settings',
        uselist=False,
        cascade="save-update, merge, expunge"
    )


class TrackedAnimeReleaseGroupPreferences(BaseModel, BaseModelMixin):
    __tablename__ = 'tracked_anime_release_group_preferences'

    tracked_anime_id: Mapped[int] = mapped_column(ForeignKey("tracked_anime.id"),  # type: ignore[arg-type]
                                                  nullable=False)
    release_group: Mapped[str] = mapped_column(nullable=False)
    episode_number_offset: Mapped[int] = mapped_column(nullable=False, default=0)
    override_match_against: Mapped[str | None] = mapped_column(nullable=True)

    tracked_anime: Mapped["TrackedAnime"] = relationship(
        'TrackedAnime',
        back_populates='release_groups_preferences',
        uselist=False,
        cascade="save-update, merge, expunge"
    )


class TrackedAnimeEpisode(BaseModel, BaseModelMixin):
    __tablename__ = 'tracked_anime_episode'

    tracked_anime_id: Mapped[int] = mapped_column(ForeignKey("tracked_anime.id"),  # type: ignore[arg-type]
                                                  nullable=False)
    episode_number: Mapped[int] = mapped_column(nullable=False)
    tvdb_series_id: Mapped[int | None] = mapped_column(nullable=True)
    tvdb_season_number: Mapped[int | None] = mapped_column(nullable=True)
    tvdb_episode_numbers: Mapped[list] = mapped_column(JSON(none_as_null=True), nullable=True)  # type: ignore[arg-type]
    tvdb_episode_ids: Mapped[list] = mapped_column(JSON(none_as_null=True), nullable=False)  # type: ignore[arg-type]
    tvdb_episode_part: Mapped[int | None] = mapped_column(nullable=True)
    tvdb_episode_part_ceiling: Mapped[int | None] = mapped_column(nullable=True)
    auto_discard: Mapped[bool] = mapped_column(nullable=False, default=False)

    tracked_anime: Mapped[TrackedAnime] = relationship(
        'TrackedAnime',
        back_populates='episodes',
        uselist=False,
        cascade="save-update, merge, expunge"
    )
    torrents: Mapped[list["Torrent"]] = relationship(
        'Torrent',
        back_populates='tracked_anime_episode',
        uselist=True,
        cascade="save-update, merge, expunge"
    )


class Torrent(BaseModel, BaseModelMixin):
    __tablename__ = 'torrent'

    magnet_hash: Mapped[str] = mapped_column(nullable=False)
    tracked_anime_episode_id: Mapped[int] = (
        mapped_column(ForeignKey("tracked_anime_episode.id"), nullable=False)  # type: ignore[arg-type]
    )
    parent_torrent_id: Mapped[int] = mapped_column(ForeignKey("torrent.id"),  # type: ignore[arg-type]
                                                   nullable=True)
    rss_xml: Mapped[str] = mapped_column(nullable=False)
    torrent_link: Mapped[str] = mapped_column(nullable=False)
    torrent_title: Mapped[str] = mapped_column(nullable=False)
    override: Mapped[bool] = mapped_column(nullable=False, default=False)
    discarded: Mapped[bool] = mapped_column(nullable=False, default=False)
    release_group: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    episode_number: Mapped[int] = mapped_column(nullable=False)
    episode_part: Mapped[int] = mapped_column(nullable=False, default=0)
    episode_part_ceiling: Mapped[int] = mapped_column(nullable=False, default=0)
    language_code: Mapped[str] = mapped_column(nullable=False, default="und")
    encoding: Mapped[Encoding] = mapped_column(Encoding.as_orm_enum(), nullable=False)
    resolution: Mapped[Resolution] = mapped_column(Resolution.as_orm_enum(), nullable=False)
    version_number: Mapped[int] = mapped_column(nullable=False, default=1)
    repack_indicator: Mapped[bool] = mapped_column(nullable=False, default=False)
    source: Mapped[VideoSource] = mapped_column(VideoSource.as_orm_enum(), nullable=False, default=VideoSource.OTHER)

    tracked_anime_episode: Mapped["TrackedAnimeEpisode"] = relationship(
        'TrackedAnimeEpisode',
        back_populates='torrents',
        uselist=False,
        cascade="save-update, merge, expunge"
    )
    download: Mapped["TorrentDownload"] = relationship(
        'TorrentDownload',
        back_populates='torrent',
        uselist=False,
        cascade="save-update, merge, expunge"
    )
    parent_torrent: Mapped["Torrent"] = relationship(
        'Torrent',
        back_populates='child_torrents',
        remote_side='Torrent.id',
        uselist=False,
        cascade="save-update, merge, expunge"
    )
    child_torrents: Mapped[list["Torrent"]] = relationship(
        'Torrent',
        back_populates='parent_torrent',
        uselist=True,
        cascade="save-update, merge, expunge"
    )

    def has_active_download(self):
        return self.effective_download and self.effective_download.status not in [TorrentDownloadStatus.DELETED,
                                                                                  TorrentDownloadStatus.DISCARDED]

    @property
    def effective_download(self):
        if self.download:
            return self.download
        elif self.parent_torrent and self.parent_torrent.download:
            return self.parent_torrent.download
        return None

    @property
    def nyaa_id(self) -> str | None:
        if "nyaa.si" in self.torrent_link:
            return self.torrent_link.split('/')[-1].split('.torrent')[0]
        return None


class TorrentDownload(BaseModel, BaseModelMixin):
    __tablename__ = 'torrent_download'

    torrent_id: Mapped[int] = mapped_column(ForeignKey("torrent.id"),  # type: ignore[arg-type]
                                            nullable=False)
    status: Mapped[TorrentDownloadStatus] = mapped_column(TorrentDownloadStatus.as_orm_enum(), nullable=False)
    status_retry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    status_details: Mapped[str | None] = mapped_column(nullable=True)
    download_directory_path: Mapped[str | None] = mapped_column(nullable=True)
    source_path: Mapped[str | None] = mapped_column(nullable=True)
    destination_path: Mapped[str] = mapped_column(nullable=True)
    copied_to_destination_path_at: Mapped[datetime | None] = (
        mapped_column(AwareDateTime(), nullable=True)  # type: ignore[arg-type]
    )

    torrent: Mapped["Torrent"] = relationship(
        'Torrent',
        back_populates='download',
        uselist=False,
        cascade="save-update, merge, expunge"
    )


class MappingOverride(BaseModel, BaseModelMixin):
    __tablename__ = 'mapping_override'

    anilist_id: Mapped[int] = mapped_column(nullable=False)
    anilist_episode_number_from: Mapped[int] = mapped_column(nullable=False)
    anilist_episode_number_to: Mapped[int | None] = mapped_column(nullable=True)
    tvdb_series_id: Mapped[int] = mapped_column(nullable=False)
    tvdb_season_number: Mapped[int] = mapped_column(nullable=False)
    tvdb_episode_number_from: Mapped[int] = mapped_column(nullable=False)
    tvdb_episode_number_to: Mapped[int | None] = mapped_column(nullable=True)
    granularity: Mapped[int] = mapped_column(nullable=False, default=1)
    mode: Mapped[MappingOverrideMode] = mapped_column(MappingOverrideMode.as_orm_enum(), nullable=False)


class Notification(BaseModel, BaseModelMixin):
    __tablename__ = 'notification'

    code: Mapped[NotificationCode] = mapped_column(NotificationCode.as_orm_enum(), nullable=False)
    level: Mapped[NotificationLevel] = mapped_column(NotificationLevel.as_orm_enum(), nullable=False)
    text: Mapped[str] = mapped_column(nullable=False)
    identifier: Mapped[dict | None] = mapped_column(JSON(none_as_null=True), nullable=True)  # type: ignore[arg-type]
    status: Mapped[NotificationStatus] = mapped_column(NotificationStatus.as_orm_enum(), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(AwareDateTime(),  # type: ignore[arg-type]
                                                   nullable=False)


class AuditLog(BaseModel, BaseModelMixin):
    __tablename__ = 'audit_log'

    code: Mapped[AuditLogCode] = mapped_column(AuditLogCode.as_orm_enum(), nullable=False)
    category: Mapped[AuditLogCategory] = mapped_column(AuditLogCategory.as_orm_enum(), nullable=False)
    text: Mapped[str] = mapped_column(nullable=False)
    data: Mapped[dict] = mapped_column(JSON(none_as_null=True), nullable=False)  # type: ignore[arg-type]
    context_id: Mapped[str] = mapped_column(nullable=False)


class CachedAsset(BaseModel, BaseModelMixin):
    __tablename__ = 'cached_asset'

    asset_filename: Mapped[str] = mapped_column(nullable=False, unique=True)
    asset_type: Mapped[CachedAssetType] = mapped_column(CachedAssetType.as_orm_enum(), nullable=False)
    remote: Mapped[str] = mapped_column(nullable=False, unique=True)
    remote_type: Mapped[CachedAssetRemoteType] = mapped_column(CachedAssetRemoteType.as_orm_enum(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(AwareDateTime(), nullable=False)  # type: ignore[arg-type]
    deletable: Mapped[bool] = mapped_column(nullable=False, default=True)
