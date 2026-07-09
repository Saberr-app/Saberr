from datetime import datetime

from pydantic import BaseModel

from api.schemas import cached_asset, int_in_range, NonEmptyString
from api.schemas.anime_schemas import AnimeItemBase, AnimeItem
from constants import TVDBSeasonType, Encoding, Resolution, VideoSource, ReleaseCriteriaProperty, \
    AnilistAnimeUserStatus, TVDBFinaleType, TorrentDownloadStatus, TrackedAnimeStatus


class TrackedAnimeRawSettings(BaseModel):
    raw_episode_file_name_format: NonEmptyString


class TrackedAnimeTVDBSettings(BaseModel):
    tvdb_season_type: TVDBSeasonType
    season_number_padding: int_in_range(ge=1)
    season_directory_number_padding: int_in_range(ge=1)
    season_directory_name_format: NonEmptyString
    episode_file_name_format: NonEmptyString
    titleless_episode_file_name_format: NonEmptyString


class TrackedAnimeReleaseGroupSettings(BaseModel):
    release_group_name: NonEmptyString  # validated during request
    episode_number_offset: int = 0
    override_match_against: NonEmptyString | None = None


class TrackedAnimeReleaseProfileSettingsCreateRequest(BaseModel):
    preferred_release_groups: list[NonEmptyString]
    preferred_encodings: list[Encoding]
    preferred_resolutions: list[Resolution]
    preferred_language_codes: list[NonEmptyString]
    preferred_sources: list[VideoSource]
    language_codes_restricted: bool = False
    sources_restricted: bool = False
    accept_release_upgrades: bool = True
    priorities_sorted: list[ReleaseCriteriaProperty]  # validated during request


class TrackedAnimeReleaseProfileSettings(TrackedAnimeReleaseProfileSettingsCreateRequest):
    id: int


class TrackedAnimeCreateRequest(BaseModel):
    anilist_id: int_in_range(ge=1)
    from_episode: int_in_range(ge=1)
    show_parent_directory: NonEmptyString
    show_folder_name: NonEmptyString
    episode_number_padding: int_in_range(ge=1)
    tvdb_structure_enabled: bool

    release_profile: TrackedAnimeReleaseProfileSettingsCreateRequest | None = None
    raw_settings: TrackedAnimeRawSettings
    tvdb_settings: TrackedAnimeTVDBSettings
    release_group_settings: list[TrackedAnimeReleaseGroupSettings]


class TrackedAnimeItem(TrackedAnimeCreateRequest):

    class UserAnimeListItem(BaseModel):
        progress: int
        score: float | int
        status: AnilistAnimeUserStatus
        repeat_count: int
        is_private: bool
        started_at: AnimeItem.AnilistDate
        completed_at: AnimeItem.AnilistDate
        notes: str | None

    class EpisodeStats(BaseModel):
        latest_known_episode_number: int | None
        processed_episode_count: int
        downloading_episode_count: int
        failed_episode_count: int

    id: int
    status: TrackedAnimeStatus
    anime: AnimeItemBase
    user_entry: UserAnimeListItem | None
    release_profile: TrackedAnimeReleaseProfileSettings | None = None
    episode_stats: EpisodeStats


class TrackedAnimeItemEpisode(BaseModel):

    class TVDBSeriesEpisode(BaseModel):
        id: int
        series_id: int
        title: str | None
        air_date: datetime | None
        runtime: int | None
        overview: str | None
        image_url: cached_asset()
        number: int
        absolute_number: int
        season_number: int
        season_name: str | None
        finale_type: TVDBFinaleType | None

    episode_number: int
    tvdb_series_episodes: list[TVDBSeriesEpisode]
    tvdb_episode_part: int | None
    tvdb_episode_part_ceiling: int | None
    auto_discard: bool
    # latest torrent_download record whose status is not deleted or discarded
    download_id: int | None
    download_status: TorrentDownloadStatus | None


class TrackedAnimeItemEpisodeList(BaseModel):
    episodes: list[TrackedAnimeItemEpisode]


class TrackedAnimeItemWithEpisodes(TrackedAnimeItem, TrackedAnimeItemEpisodeList):
    pass


class TrackedAnimeListResponse(BaseModel):
    tracked_anime: list[TrackedAnimeItem]
    releasing_watching_not_tracked_count: int
    releasing_planning_not_tracked_count: int


class TrackedAnimeUpdateRequest(BaseModel):
    unarchive: bool | None = None
    from_episode: int_in_range(ge=1)
    show_parent_directory: NonEmptyString
    show_folder_name: NonEmptyString
    episode_number_padding: int_in_range(ge=1)
    tvdb_structure_enabled: bool

    release_profile: TrackedAnimeReleaseProfileSettings | None
    raw_settings: TrackedAnimeRawSettings
    tvdb_settings: TrackedAnimeTVDBSettings
    release_group_settings: list[TrackedAnimeReleaseGroupSettings]


class TrackedAnimeBatchArchiveRequest(BaseModel):
    anilist_ids: list[int]


class TrackedAnimeBatchDeleteRequest(BaseModel):
    anilist_ids: list[int]


class TrackedAnimeItemEpisodeDetails(TrackedAnimeItemEpisode):

    class EpisodeTorrentItem(BaseModel):

        class Download(BaseModel):
            id: int
            status: TorrentDownloadStatus
            status_details: str | None
            download_directory_path: str | None
            destination_path: str | None
            copied_to_destination_path_at: datetime | None

            qbit_status: str | None = None
            qbit_progress: float | None = None
            qbit_eta: int | None = None

        class RawTorrent(BaseModel):
            title: str
            description: str
            web_link: str
            size: str

            release_group: str | None = None
            anime_title: str | None = None
            episode_number: int | None = None
            version_number: int | None = None
            language_code: str | None = None
            repack_indicator: bool | None = None
            resolution: Resolution | None = None
            source: VideoSource | None = None
            encoding: Encoding | None = None

        parent_id: int
        children_ids: list[int]
        raw_torrent: RawTorrent
        download: Download | None
        effective_date: datetime

    torrents: list[EpisodeTorrentItem]


class TrackedAnimeEpisodeUpdateRequest(BaseModel):
    auto_discard: bool
