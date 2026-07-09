from datetime import datetime

from pydantic import BaseModel

from constants import TorrentDownloadStatus, Encoding, Resolution, VideoSource


class DownloadItem(BaseModel):
    class Torrent(BaseModel):
        id: int
        web_link: str
        magnet_hash: str
        release_group: str
        title: str
        size: str
        encoding: Encoding
        resolution: Resolution
        source: VideoSource
        language_code: str
        version_number: int
        repack_indicator: bool

    class Anime(BaseModel):
        anilist_id: int
        tracked_anime_id: int
        anilist_english_title: str | None
        anilist_native_title: str | None
        anilist_romaji_title: str

    class QBitStatus(BaseModel):
        status: str
        progress: float
        eta: int | None

    id: int
    status: TorrentDownloadStatus
    status_details: str | None
    download_directory_path: str | None
    source_path: str | None
    destination_path: str | None
    copied_to_destination_path_at: datetime | None
    created_at: datetime
    superseded: bool
    anime: Anime
    anilist_episode_numbers: list[int]
    anilist_episode_part: int = 0
    anilist_episode_part_ceiling: int = 0
    torrent: Torrent
    qbit_status: QBitStatus | None


class DownloadListResponse(BaseModel):
    downloads: list[DownloadItem]


class DownloadListRequest(BaseModel):
    offset: int = 0
    limit: int = 50
    statuses: list[TorrentDownloadStatus] = []


class DownloadRetryCheck(BaseModel):
    superseded: bool


class DownloadUpdatesStreamRequest(BaseModel):
    freq: int = 3
    download_ids: list[int]


class DownloadUpdatesStreamResponse(BaseModel):

    class DownloadStreamItem(BaseModel):
        id: int
        status: TorrentDownloadStatus | None = None
        status_details: str | None = None
        download_directory_path: str | None = None
        source_path: str | None = None
        destination_path: str | None = None
        copied_to_destination_path_at: datetime | None = None
        qbit_status: str | None = None
        qbit_progress: float | None = None
        qbit_eta: int | None = None
        deleted: bool | None = None

    ref: int
    changed: list[DownloadStreamItem]


class DeleteDownloadRequest(BaseModel):
    delete_from_qbit: bool
    delete_from_disk: bool

    delete_imported_file: bool
    discard_torrent: bool
