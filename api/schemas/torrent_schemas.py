from datetime import datetime

from pydantic import BaseModel

from api.schemas import NonEmptyString
from constants import Resolution, VideoSource, Encoding, TorrentDownloadStatus, ReleaseCriteriaProperty


class TorrentListItem(BaseModel):

    class Note(BaseModel):
        text: str
        is_error: bool

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

    class RSSTorrent(BaseModel):

        class RSSTorrentResolvedAttributes(BaseModel):
            release_group: str | None
            title: str | None
            episode_number: int | None
            version_number: int | None
            language_code: str | None
            repack_indicator: bool | None
            resolution: Resolution | None
            source: VideoSource | None
            encoding: Encoding | None
            censorship_status: bool | None
            is_batch: bool
            missing_required: bool

        title: str
        web_link: str
        seeders: int
        leechers: int
        downloads: int
        magnet_hash: str
        category: str
        size: int
        description: str
        created_at: datetime
        rss_xml: str

        # must add even if regex didn't work - fill release_group and is_batch
        explicit_resolved_attributes: RSSTorrentResolvedAttributes | None
        # fallback - always filled
        fuzzy_resolved_attributes: RSSTorrentResolvedAttributes

    rss_torrent: RSSTorrent
    download: Download | None
    anilist_id: int | None
    anilist_english_title: str | None
    anilist_native_title: str | None
    anilist_romaji_title: str | None

    parent_id: int | None
    children_ids: list[int]
    tracked_anime_id: int | None
    tracked_from_episode: int | None

    anilist_episode_numbers: list[int]
    anilist_episode_part: int = 0
    anilist_episode_part_ceiling: int = 0

    selected: bool
    superseded: bool
    discarded: bool
    profile_shortcomings: list[ReleaseCriteriaProperty]
    notes: list[Note]


class TorrentPullStatus(BaseModel):
    ref: int
    last_pull: datetime | None
    next_pull: datetime | None
    currently_pulling: bool


class TorrentListResponse(BaseModel):
    torrents: list[TorrentListItem]
    pull_status: TorrentPullStatus


class TorrentSearchRequest(BaseModel):
    release_groups: list[NonEmptyString] | None = None
    query: NonEmptyString | None = None


class TorrentDiscardRequest(BaseModel):
    magnet_hashes: list[NonEmptyString]


class TorrentDownloadRequest(BaseModel):

    class ReleaseGroupOverrideSettings(BaseModel):
        episode_number_offset: int = 0
        override_match_against: NonEmptyString

    magnet_hash: NonEmptyString
    tracked_anime_id: int
    episode_numbers: list[int]
    episode_part: int = 0
    episode_part_ceiling: int = 0

    release_group: NonEmptyString
    language_code: NonEmptyString = "und"
    resolution: Resolution
    source: VideoSource
    encoding: Encoding
    version: int = 1
    is_repack: bool = False
    rss_xml: NonEmptyString

    discard_future_torrents: bool = False
    release_group_override_settings: ReleaseGroupOverrideSettings | None = None


class TorrentDownloadResponse(BaseModel):

    class RSSTorrent(TorrentListItem.RSSTorrent):
        explicit_resolved_attributes: TorrentListItem.RSSTorrent.RSSTorrentResolvedAttributes
        fuzzy_resolved_attributes: None = None

    download: TorrentListItem.Download | None
    rss_torrent: RSSTorrent

    anilist_id: int | None
    anilist_english_title: str | None
    anilist_native_title: str | None
    anilist_romaji_title: str | None

    parent_id: int | None
    children_ids: list[int]
    tracked_anime_id: int | None
    tracked_from_episode: int | None

    anilist_episode_numbers: list[int]
    anilist_episode_part: int | None
    anilist_episode_part_ceiling: int | None


class TorrentOverrideRequest(BaseModel):
    discard_future_torrents: bool = False


class TorrentOverrideResponse(BaseModel):
    download_id: int
