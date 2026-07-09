from enum import Enum as BIEnum
from sqlalchemy import Enum as ORMEnum


class Enum(BIEnum):
    @classmethod
    def as_list(cls):
        return [value.value for key, value in cls.__dict__.items()
                if not key.startswith('_') and not key.endswith('__') and hasattr(value, "value")]

    @classmethod
    def as_orm_enum(cls):
        return ORMEnum(cls, name=cls.__name__,
                       values_callable=lambda enum_cls: [member.value for member in enum_cls])


DOWNLOAD_PROCESSING_RETRY_LIMIT = 5
ANILIST_AUTH_LINK = "https://anilist.co/api/v2/oauth/authorize?client_id=41692&response_type=token"
TV_PUBLIC_API_KEY = "d7f5baa1-1d46-4ff1-ab6f-6279948ebf5d"
JWT_ALGORITHM = "HS256"


class AppContext(Enum):
    CONSOLE = "console"
    WINDOWS = "windows"


class ExternalLink:
    ANILIST_ANIME = "https://anilist.co/anime/{id}"
    MAL_ANIME = "https://myanimelist.net/anime/{id}"
    NYAA_TORRENT = "https://nyaa.si/view/{id}"
    TVDB_SERIES = "https://thetvdb.com/?tab=series&id={id}"
    IMDB_TITLE = "https://www.imdb.com/title/{id}"


class AppAsset:
    ICON = "assets/icon.png"
    LOGO_PNG = "assets/logo.png"


class CachedAssetType(Enum):
    RELATIONS = "relations"
    OTHER = "other"


class MetadataSource(Enum):
    ANILIST = "ANILIST"
    TVDB = "TVDB"


#### DB Enums ####


class SettingsCode(Enum):
    # Anilist Settings
    ANILIST_USERNAME = "ANILIST_USERNAME"  # user can set this
    ANILIST_USER_TOKEN = "ANILIST_USER_TOKEN"  # stored after auth, app-managed
    ANILIST_USER_DATA = "ANILIST_USER_DATA"  # stored after auth, app-managed

    # qBit client settings
    QBIT_BASE_URL = "QBIT_BASE_URL"
    QBIT_USERNAME = "QBIT_USERNAME"
    QBIT_PASSWORD = "QBIT_PASSWORD"
    QBIT_REMOTE_PATH_MAPPING = "QBIT_REMOTE_PATH_MAPPING"

    # Post-download processing settings
    DEFAULT_DESTINATION_DIRECTORY = "DEFAULT_DESTINATION_DIRECTORY"
    DEFAULT_SHOW_DIRECTORY_NAME_FORMAT = "DEFAULT_SHOW_DIRECTORY_NAME_FORMAT"
    DEFAULT_SEASON_DIRECTORY_NAME_FORMAT = "DEFAULT_SEASON_DIRECTORY_NAME_FORMAT"
    DEFAULT_RAW_EPISODE_FILE_NAME_FORMAT = "DEFAULT_RAW_EPISODE_FILE_NAME_FORMAT"
    DEFAULT_EPISODE_FILE_NAME_FORMAT = "DEFAULT_EPISODE_FILE_NAME_FORMAT"
    DEFAULT_TITLELESS_EPISODE_FILE_NAME_FORMAT = "DEFAULT_TITLELESS_EPISODE_FILE_NAME_FORMAT"

    # Other settings
    TVDB_STRUCTURE_ENABLED_DEFAULT = "TVDB_STRUCTURE_ENABLED_DEFAULT"
    TORRENT_CATEGORY = "TORRENT_CATEGORY"
    STAGING_DIRECTORY = "STAGING_DIRECTORY"  # download location for torrent files before processing
    ORGANIZE_DOWNLOADS = "ORGANIZE_DOWNLOADS"  # toggle for organizing downloads into directories
    APPLY_RELEASE_GROUP_AS_TORRENT_TAG = "APPLY_RELEASE_GROUP_AS_TORRENT_TAG"
    APPLY_ENCODING_AS_TORRENT_TAG = "APPLY_ENCODING_AS_TORRENT_TAG"
    APPLY_RESOLUTION_AS_TORRENT_TAG = "APPLY_RESOLUTION_AS_TORRENT_TAG"
    APPLY_LANGUAGE_CODE_AS_TORRENT_TAG = "APPLY_LANGUAGE_CODE_AS_TORRENT_TAG"
    APPLY_ANIME_TITLE_AS_TORRENT_TAG = "APPLY_ANIME_TITLE_AS_TORRENT_TAG"

    AUTO_DOWNLOAD = "AUTO_DOWNLOAD"  # toggle for auto-downloading
    RSS_CHECK_FREQUENCY = "RSS_CHECK_FREQUENCY"
    RSS_CATEGORY = "RSS_CATEGORY"

    SET_DOWNLOAD_AS_FAILED_AFTER_MINUTES = "SET_DOWNLOAD_AS_FAILED_AFTER_MINUTES"
    SET_PROCESSING_AS_FAILED_AFTER_MINUTES = "SET_PROCESSING_AS_FAILED_AFTER_MINUTES"
    NOTIFICATIONS_DISCORD_WEBHOOK_URL = "NOTIFICATIONS_DISCORD_WEBHOOK_URL"
    DISCORD_WEBHOOK_USERNAME = "DISCORD_WEBHOOK_USERNAME"
    DISCORD_WEBHOOK_AVATAR_URL = "DISCORD_WEBHOOK_AVATAR_URL"
    DISCORD_NOTIFY_ON_LOGIN = "DISCORD_NOTIFY_ON_LOGIN"
    DISCORD_NOTIFY_ON_DOWNLOAD_PROCESSED = "DISCORD_NOTIFY_ON_DOWNLOAD_PROCESSED"
    DISCORD_NOTIFY_ON_UPGRADE_DOWNLOAD_PROCESSED = "DISCORD_NOTIFY_ON_UPGRADE_DOWNLOAD_PROCESSED"
    DISCORD_NOTIFY_ON_DOWNLOAD_FAILED = "DISCORD_NOTIFY_ON_DOWNLOAD_FAILED"
    DISCORD_USER_ID = "DISCORD_USER_ID"  # complements webhook url, used to ping the user for errors
    TIMEZONE = "TIMEZONE"
    ANILIST_PREFERRED_TITLE_LANGUAGE = "ANILIST_PREFERRED_TITLE_LANGUAGE"
    PUBLISHED_URL = "PUBLISHED_URL"


SETTINGS_CODE_FRIENDLY_NAME_MAP = {
    SettingsCode.ANILIST_USERNAME: "AniList Username",
    SettingsCode.ANILIST_USER_TOKEN: "AniList User Token",
    SettingsCode.ANILIST_USER_DATA: "AniList User Data",
    SettingsCode.QBIT_BASE_URL: "qBittorrent Base URL",
    SettingsCode.QBIT_USERNAME: "qBittorrent Username",
    SettingsCode.QBIT_PASSWORD: "qBittorrent Password",
    SettingsCode.QBIT_REMOTE_PATH_MAPPING: "qBittorrent Remote Path Mapping",
    SettingsCode.DEFAULT_DESTINATION_DIRECTORY: "Default Destination Directory",
    SettingsCode.DEFAULT_SHOW_DIRECTORY_NAME_FORMAT: "Default Show Directory Name Format",
    SettingsCode.DEFAULT_SEASON_DIRECTORY_NAME_FORMAT: "Default Season Directory Name Format",
    SettingsCode.DEFAULT_RAW_EPISODE_FILE_NAME_FORMAT: "Default Raw Episode File Name Format",
    SettingsCode.DEFAULT_EPISODE_FILE_NAME_FORMAT: "Default Episode File Name Format",
    SettingsCode.DEFAULT_TITLELESS_EPISODE_FILE_NAME_FORMAT: "Default Titleless Episode File Name Format",
    SettingsCode.TVDB_STRUCTURE_ENABLED_DEFAULT: "TVDB Structure Enabled by Default",
    SettingsCode.TORRENT_CATEGORY: "Torrent Category",
    SettingsCode.STAGING_DIRECTORY: "Staging Directory",
    SettingsCode.ORGANIZE_DOWNLOADS: "Organize Downloads",
    SettingsCode.APPLY_RELEASE_GROUP_AS_TORRENT_TAG: "Apply Release Group as Torrent Tag",
    SettingsCode.APPLY_ENCODING_AS_TORRENT_TAG: "Apply Encoding as Torrent Tag",
    SettingsCode.APPLY_RESOLUTION_AS_TORRENT_TAG: "Apply Resolution as Torrent Tag",
    SettingsCode.APPLY_LANGUAGE_CODE_AS_TORRENT_TAG: "Apply Language Code as Torrent Tag",
    SettingsCode.APPLY_ANIME_TITLE_AS_TORRENT_TAG: "Apply Anime Title as Torrent Tag",
    SettingsCode.AUTO_DOWNLOAD: "Auto Download",
    SettingsCode.RSS_CHECK_FREQUENCY: "RSS Check Frequency",
    SettingsCode.RSS_CATEGORY: "RSS Category",
    SettingsCode.SET_DOWNLOAD_AS_FAILED_AFTER_MINUTES: "Set Download as Failed After (Minutes)",
    SettingsCode.SET_PROCESSING_AS_FAILED_AFTER_MINUTES: "Set Processing as Failed After (Minutes)",
    SettingsCode.NOTIFICATIONS_DISCORD_WEBHOOK_URL: "Notifications Discord Webhook URL",
    SettingsCode.DISCORD_WEBHOOK_USERNAME: "Discord Webhook Username",
    SettingsCode.DISCORD_WEBHOOK_AVATAR_URL: "Discord Webhook Avatar URL",
    SettingsCode.DISCORD_NOTIFY_ON_LOGIN: "Discord - Notify on New Login",
    SettingsCode.DISCORD_NOTIFY_ON_DOWNLOAD_PROCESSED: "Discord - Notify on Episode Imported",
    SettingsCode.DISCORD_NOTIFY_ON_UPGRADE_DOWNLOAD_PROCESSED: "Discord - Notify on Episode Upgraded",
    SettingsCode.DISCORD_NOTIFY_ON_DOWNLOAD_FAILED: "Discord - Notify on Download/Import Failed",
    SettingsCode.DISCORD_USER_ID: "Discord User ID",
    SettingsCode.TIMEZONE: "Timezone",
    SettingsCode.ANILIST_PREFERRED_TITLE_LANGUAGE: "AniList Preferred Title Language",
    SettingsCode.PUBLISHED_URL: "Published URL",
}


class TrackedAnimeStatus(Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class TVDBSeasonType(Enum):
    OFFICIAL = "official"
    ABSOLUTE = "absolute"
    DVD = "dvd"
    ALTERNATE = "alternate"
    REGIONAL = "regional"


class TorrentDownloadStatus(Enum):
    PENDING = "PENDING"  # should never really be in this state in the db
    DOWNLOADING = "DOWNLOADING"  # post_download_processing & stuck_check
    DOWNLOADED = "DOWNLOADED"  # post_download_processing
    PROCESSING = "PROCESSING"  # process_download & stuck_check
    PROCESSED = "PROCESSED"  # final status
    FAILED_DOWNLOAD_INIT = "FAILED_DOWNLOAD_INIT"  # post_download_processing
    FAILED_DOWNLOAD = "FAILED_DOWNLOAD"  # post_download_processing
    FAILED_PROCESSING = "FAILED_PROCESSING"  # post_download_processing
    DELETED = "DELETED"  # final status
    DISCARDED = "DISCARDED"  # final status


TORRENT_DOWNLOAD_STATUS_PRIORITY_LIST = [
    # relevant for deciding the most relevant download status of an episode
    TorrentDownloadStatus.PROCESSED,
    TorrentDownloadStatus.PROCESSING,
    TorrentDownloadStatus.DOWNLOADED,
    TorrentDownloadStatus.DOWNLOADING,
    TorrentDownloadStatus.PENDING,
    TorrentDownloadStatus.FAILED_PROCESSING,
    TorrentDownloadStatus.FAILED_DOWNLOAD,
    TorrentDownloadStatus.FAILED_DOWNLOAD_INIT,
    TorrentDownloadStatus.DELETED,
    TorrentDownloadStatus.DISCARDED,
]


class MappingOverrideMode(Enum):
    IF_MISSING = "IF_MISSING"
    ALWAYS = "ALWAYS"


class NotificationLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class NotificationCode(Enum):
    # errors
    DOWNLOAD_PROCESSING_PERMANENTLY_FAILED = "DOWNLOAD_PROCESSING_PERMANENTLY_FAILED"
    UNCATEGORIZED_ERROR = "UNCATEGORIZED_ERROR"
    # warnings
    SERVICE_DOWN = "SERVICE_DOWN"
    UNCATEGORIZED_WARNING = "UNCATEGORIZED_WARNING"
    # info
    GENERAL = "GENERAL"
    LOGIN = "LOGIN"


class NotificationStatus(Enum):
    UNREAD = "UNREAD"
    READ = "READ"
    STALE = "STALE"


class AuditLogCategory(Enum):
    APP = "APP"
    MAPPING_OVERRIDES = "MAPPING_OVERRIDES"
    TORRENT_SELECTION = "TORRENT_SELECTION"
    TORRENT_PROCESSING = "TORRENT_PROCESSING"
    TRACKED_ANIME = "TRACKED_ANIME"
    ANILIST = "ANILIST"
    EXTERNAL_SERVICE = "EXTERNAL_SERVICE"
    OTHER = "OTHER"


class AuditLogCode(Enum):
    APP_STARTED = "APP_STARTED"
    APP_EXITED = "APP_EXITED"
    LOGIN_SUCCEEDED = "LOGIN_SUCCEEDED"
    LOGIN_FAILED = "LOGIN_FAILED"
    SETTING_CHANGED = "SETTING_CHANGED"

    MAPPING_OVERRIDE_ADDED = "MAPPING_OVERRIDE_ADDED"
    MAPPING_OVERRIDE_UPDATED = "MAPPING_OVERRIDE_UPDATED"
    MAPPING_OVERRIDE_DELETED = "MAPPING_OVERRIDE_DELETED"

    TORRENT_DISCARDED = "TORRENT_DISCARDED"
    TORRENT_SELECTED = "TORRENT_SELECTED"
    TORRENT_MANUALLY_SELECTED = "TORRENT_MANUALLY_SELECTED"

    TORRENT_DOWNLOAD_STARTED = "TORRENT_DOWNLOAD_STARTED"
    TORRENT_DOWNLOAD_FINISHED = "TORRENT_DOWNLOAD_FINISHED"
    TORRENT_DOWNLOAD_FAILED = "TORRENT_DOWNLOAD_FAILED"
    TORRENT_DOWNLOAD_DISCARDED = "TORRENT_DOWNLOAD_DISCARDED"
    TORRENT_DOWNLOAD_DELETED = "TORRENT_DOWNLOAD_DELETED"
    TORRENT_PROCESSING_STARTED = "TORRENT_PROCESSING_STARTED"
    TORRENT_PROCESSING_FINISHED = "TORRENT_PROCESSING_FINISHED"
    TORRENT_PROCESSING_FAILED = "TORRENT_PROCESSING_FAILED"

    TRACKED_ANIME_ADDED = "TRACKED_ANIME_ADDED"
    TRACKED_ANIME_UPDATED = "TRACKED_ANIME_UPDATED"
    TRACKED_ANIME_REMOVED = "TRACKED_ANIME_REMOVED"
    TRACKED_ANIME_ARCHIVED = "TRACKED_ANIME_ARCHIVED"

    ANILIST_ANIME_ADDED = "ANILIST_ANIME_ADDED"
    ANILIST_ANIME_UPDATED = "ANILIST_ANIME_UPDATED"
    ANILIST_ANIME_DELETED = "ANILIST_ANIME_DELETED"
    BATCH_ANILIST_ANIME_ADDED = "BATCH_ANILIST_ANIME_ADDED"
    BATCH_ANILIST_ANIME_UPDATED = "BATCH_ANILIST_ANIME_UPDATED"
    BATCH_ANILIST_ANIME_DELETED = "BATCH_ANILIST_ANIME_DELETED"
    ANILIST_LIST_REFRESHED = "ANILIST_LIST_REFRESHED"

    SERVICE_SET_OFFLINE = "SERVICE_SET_OFFLINE"
    SERVICE_SET_ONLINE = "SERVICE_SET_ONLINE"

    ANIME_RELATIONS_REFRESHED = "ANIME_RELATIONS_REFRESHED"
    OTHER = "OTHER"


AUDIT_LOG_CATEGORY_TO_CODE_MAP = {
    AuditLogCategory.APP: {AuditLogCode.APP_STARTED,
                           AuditLogCode.APP_EXITED,
                           AuditLogCode.LOGIN_SUCCEEDED,
                           AuditLogCode.LOGIN_FAILED,
                           AuditLogCode.SETTING_CHANGED},
    AuditLogCategory.MAPPING_OVERRIDES: {AuditLogCode.MAPPING_OVERRIDE_ADDED,
                                         AuditLogCode.MAPPING_OVERRIDE_UPDATED,
                                         AuditLogCode.MAPPING_OVERRIDE_DELETED},
    AuditLogCategory.TORRENT_SELECTION: {AuditLogCode.TORRENT_DISCARDED,
                                         AuditLogCode.TORRENT_SELECTED,
                                         AuditLogCode.TORRENT_MANUALLY_SELECTED},
    AuditLogCategory.TORRENT_PROCESSING: {AuditLogCode.TORRENT_DOWNLOAD_STARTED,
                                          AuditLogCode.TORRENT_DOWNLOAD_FINISHED,
                                          AuditLogCode.TORRENT_DOWNLOAD_FAILED,
                                          AuditLogCode.TORRENT_DOWNLOAD_DISCARDED,
                                          AuditLogCode.TORRENT_DOWNLOAD_DELETED,
                                          AuditLogCode.TORRENT_PROCESSING_STARTED,
                                          AuditLogCode.TORRENT_PROCESSING_FINISHED,
                                          AuditLogCode.TORRENT_PROCESSING_FAILED},
    AuditLogCategory.TRACKED_ANIME: {AuditLogCode.TRACKED_ANIME_ADDED,
                                     AuditLogCode.TRACKED_ANIME_UPDATED,
                                     AuditLogCode.TRACKED_ANIME_REMOVED,
                                     AuditLogCode.TRACKED_ANIME_ARCHIVED},
    AuditLogCategory.ANILIST: {AuditLogCode.ANILIST_ANIME_ADDED,
                               AuditLogCode.ANILIST_ANIME_UPDATED,
                               AuditLogCode.ANILIST_ANIME_DELETED,
                               AuditLogCode.BATCH_ANILIST_ANIME_ADDED,
                               AuditLogCode.BATCH_ANILIST_ANIME_UPDATED,
                               AuditLogCode.BATCH_ANILIST_ANIME_DELETED,
                               AuditLogCode.ANILIST_LIST_REFRESHED},
    AuditLogCategory.EXTERNAL_SERVICE: {AuditLogCode.SERVICE_SET_OFFLINE,
                                        AuditLogCode.SERVICE_SET_ONLINE},
    AuditLogCategory.OTHER: {AuditLogCode.ANIME_RELATIONS_REFRESHED,
                             AuditLogCode.OTHER}
}
AUDIT_LOG_CODE_TO_CATEGORY_MAP = {code: category for category, codes
                                  in AUDIT_LOG_CATEGORY_TO_CODE_MAP.items()
                                  for code in codes}


class CachedAssetRemoteType(Enum):
    URL = "URL"
    SCRIPT = "SCRIPT"


class ReleaseCriteriaProperty(Enum):
    VERSION = "version"
    RELEASE_GROUP = "release_group"
    RESOLUTION = "resolution"
    SOURCE = "source"
    ENCODING = "encoding"
    LANGUAGE_CODE = "language_code"


#### Other Enums ####


class WorkerName(Enum):  # sync with FE on enum name change
    CLEANUP_IN_MEMORY_CACHES = "Clean up stale in-memory cache"
    REFRESH_ANIME_RELATIONS_CACHE = "Refresh anime relations"
    REFRESH_STALE_DB_DATA = "Refresh stale DB data"
    CLEANUP_DB_AND_DISK_CACHE = "Cache cleanup"
    REFRESH_ANIME_USER_LISTS = "Refresh user anime list"

    POST_DOWNLOAD_PROCESSING = "Advance downloads processing stage"
    STUCK_CHECK = "Mark stuck downloading/processing torrents as failed"

    POLL_DOWNSTREAM_STATUS = "Check downstream services status"

    PROCESS_NOTIFICATIONS = "Process notifications"

    CONSUME_RSS_FEEDS = "Consume RSS feed"

    CREATE_BACKUP = "Create backup"
    CLEANUP_OLD_BACKUPS = "Cleanup old backups"

    CHECK_FOR_UPDATE = "Check for update"


class RSSCategory(Enum):
    AMV = "AMV"
    ENGLISH_TRANSLATED = "English Translated"
    NON_ENGLISH_TRANSLATED = "Non-English Translated"
    RAW = "Raw"
    ALL = "All"


RSS_CATEGORY_TO_CODE_MAP = {
    RSSCategory.AMV: "1_1",
    RSSCategory.ENGLISH_TRANSLATED: "1_2",
    RSSCategory.NON_ENGLISH_TRANSLATED: "1_3",
    RSSCategory.RAW: "1_4",
    RSSCategory.ALL: "1_0",
}


class Encoding(Enum):
    HEVC = "HEVC"
    AVC = "AVC"
    AV1 = "AV1"


class Resolution(Enum):
    P480 = "480p"
    P540 = "540p"
    P720 = "720p"
    P1080 = "1080p"
    P2160 = "2160p"


class VideoSource(Enum):
    CRUNCHYROLL = "Crunchyroll"
    NETFLIX = "Netflix"
    AMAZON = "Amazon"
    DISNEY_PLUS = "Disney+"
    ADN = "Anime Digital Network"
    HIDIVE = "HIDIVE"
    HULU = "Hulu"
    OTHER = "Other"


class ReleaseGroupFilterType(Enum):
    STARTS_WITH = "startswith"
    CONTAINS = "contains"


class ReleaseTitlePart(Enum):
    RELEASE_GROUP = "release_group"
    TITLE = "title"
    SEASON_NUMBER = "season_number"
    EPISODE_NUMBER = "episode_number"
    VERSION_NUMBER = "version_number"
    LANGUAGE_CODE = "language_code"
    REPACK_INDICATOR = "repack_indicator"
    RESOLUTION = "resolution"
    SOURCE = "source"
    ENCODING = "encoding"
    CENSORSHIP_STATUS = "censorship_status"


class ReleaseGroupEpisodeNumberingAffinity(Enum):
    STRICT = "STRICT"
    CONTINUOUS_PARTS = "CONTINUOUS_PARTS"
    TVDB = "TVDB"


class AnilistAnimeSeason(Enum):
    WINTER = "WINTER"
    SPRING = "SPRING"
    SUMMER = "SUMMER"
    FALL = "FALL"


class AnilistAnimeStatus(Enum):
    FINISHED = "FINISHED"
    RELEASING = "RELEASING"
    NOT_YET_RELEASED = "NOT_YET_RELEASED"
    CANCELLED = "CANCELLED"
    HIATUS = "HIATUS"


class AnilistAnimeFormat(Enum):
    TV = "TV"
    TV_SHORT = "TV_SHORT"
    MOVIE = "MOVIE"
    SPECIAL = "SPECIAL"
    OVA = "OVA"
    ONA = "ONA"
    MUSIC = "MUSIC"


class AnilistFormat(Enum):
    TV = "TV"
    TV_SHORT = "TV_SHORT"
    MOVIE = "MOVIE"
    SPECIAL = "SPECIAL"
    OVA = "OVA"
    ONA = "ONA"
    MUSIC = "MUSIC"
    MANGA = "MANGA"
    NOVEL = "NOVEL"
    ONE_SHOT = "ONE_SHOT"


class AnilistAnimeSource(Enum):
    ORIGINAL = "ORIGINAL"
    MANGA = "MANGA"
    LIGHT_NOVEL = "LIGHT_NOVEL"
    VISUAL_NOVEL = "VISUAL_NOVEL"
    VIDEO_GAME = "VIDEO_GAME"
    OTHER = "OTHER"
    NOVEL = "NOVEL"
    DOUJINSHI = "DOUJINSHI"
    ANIME = "ANIME"
    WEB_NOVEL = "WEB_NOVEL"
    LIVE_ACTION = "LIVE_ACTION"
    GAME = "GAME"
    COMIC = "COMIC"
    MULTIMEDIA_PROJECT = "MULTIMEDIA_PROJECT"
    PICTURE_BOOK = "PICTURE_BOOK"


class AnilistAnimeUserStatus(Enum):
    CURRENT = "CURRENT"
    PLANNING = "PLANNING"
    COMPLETED = "COMPLETED"
    DROPPED = "DROPPED"
    PAUSED = "PAUSED"
    REPEATING = "REPEATING"


class AnilistTitleLanguage(Enum):
    NATIVE = "Native"
    ROMAJI = "Romaji"
    ENGLISH = "English"


class AnilistScoreFormat(Enum):
    POINT_100 = "POINT_100"
    POINT_10_DECIMAL = "POINT_10_DECIMAL"
    POINT_10 = "POINT_10"
    POINT_5 = "POINT_5"
    POINT_3 = "POINT_3"


class SortDirection(Enum):
    ASC = "asc"
    DESC = "desc"


class ExternalServiceCode(Enum):
    QBIT = "qbit"
    ANILIST = "anilist"
    TVDB = "tvdb"
    RSS = "rss"
    NOTIFICATIONS_DISCORD_WEBHOOK = "notifications_discord_webhook"


class ExternalServiceErrorLevel(Enum):
    DOWN = "Down"
    AUTH_ISSUE = "Auth Issue"
    NOT_CONFIGURED = "Not Configured"
    INTERNAL_ERROR = "Internal Error"


class TVDBFinaleType(Enum):
    SERIES = "series"
    SEASON = "season"
    MIDSEASON = "midseason"


class ShowDirectoryFormattingToken(Enum):
    ANILIST_TITLE_JAPANESE = "anilist_title_japanese"
    ANILIST_TITLE_ROMAJI = "anilist_title_romaji"
    ANILIST_TITLE_ENGLISH = "anilist_title_english"
    TVDB_TITLE_ENGLISH = "tvdb_title_english"
    SEASON = "season"
    SEASON_YEAR = "season_year"
    

SHOW_DIRECTORY_FORMATTING_TOKEN_VALUE_NAME_MAP = {
    ShowDirectoryFormattingToken.ANILIST_TITLE_JAPANESE.value: "AniList Title (Japanese)",
    ShowDirectoryFormattingToken.ANILIST_TITLE_ROMAJI.value: "AniList Title (Romaji)",
    ShowDirectoryFormattingToken.ANILIST_TITLE_ENGLISH.value: "AniList Title (English)",
    ShowDirectoryFormattingToken.TVDB_TITLE_ENGLISH.value: "TVDB Title (English)",
    ShowDirectoryFormattingToken.SEASON.value: "Season",
    ShowDirectoryFormattingToken.SEASON_YEAR.value: "Season Year",
}


class SeasonDirectoryFormattingToken(Enum):
    SEASON_NUMBER = "season_number"


SEASON_DIRECTORY_FORMATTING_TOKEN_VALUE_NAME_MAP = {
    SeasonDirectoryFormattingToken.SEASON_NUMBER.value: "Season Number",
}


class EpisodeFormattingToken(Enum):
    ANILIST_TITLE_JAPANESE = "anilist_title_japanese"
    ANILIST_TITLE_ENGLISH = "anilist_title_english"
    ANILIST_TITLE_ROMAJI = "anilist_title_romaji"
    TVDB_TITLE_ENGLISH = "tvdb_title_english"
    SHOW_NAME = "show_name"

    SEASON = "season"
    SEASON_YEAR = "season_year"

    SEASON_NUMBER = "season_number"

    EPISODE_NUMBER = "episode_number"
    ABSOLUTE_EPISODE_NUMBER = "absolute_episode_number"
    EPISODE_TITLE = "episode_title"

    ENCODING = "encoding"
    RESOLUTION = "resolution"
    RELEASE_GROUP = "release_group"

    @classmethod
    def raw_episode_tokens(cls):
        return {token.value for token in [cls.ANILIST_TITLE_JAPANESE, cls.ANILIST_TITLE_ENGLISH,
                                          cls.ANILIST_TITLE_ROMAJI, cls.TVDB_TITLE_ENGLISH, cls.SHOW_NAME,
                                          cls.SEASON, cls.SEASON_YEAR, cls.EPISODE_NUMBER,
                                          cls.ENCODING, cls.RESOLUTION, cls.RELEASE_GROUP]}

    @classmethod
    def full_episode_tokens(cls) -> set[str]:
        return {token for token in cls.as_list()}

    @classmethod
    def titleless_episode_tokens(cls) -> set[str]:
        return {token for token in cls.as_list() if token != cls.EPISODE_TITLE.value}


class AiringScheduleScope(Enum):
    USER_WATCHING = "user_watching"
    USER_PLANNING = "user_planning"
    USER_TRACKING = "user_tracking"
    CURRENT_SEASON = "current_season"
    NEXT_SEASON = "next_season"
    ALL_AIRING = "all_airing"


EPISODE_FORMATTING_TOKEN_VALUE_NAME_MAP = {
    EpisodeFormattingToken.ANILIST_TITLE_JAPANESE.value: "AniList Title (Japanese)",
    EpisodeFormattingToken.ANILIST_TITLE_ENGLISH.value: "AniList Title (English)",
    EpisodeFormattingToken.ANILIST_TITLE_ROMAJI.value: "AniList Title (Romaji)",
    EpisodeFormattingToken.TVDB_TITLE_ENGLISH.value: "TVDB Title (English)",
    EpisodeFormattingToken.SHOW_NAME.value: "Show Name",
    EpisodeFormattingToken.SEASON.value: "Season",
    EpisodeFormattingToken.SEASON_YEAR.value: "Season Year",
    EpisodeFormattingToken.SEASON_NUMBER.value: "Season Number",
    EpisodeFormattingToken.EPISODE_NUMBER.value: "Episode Number",
    EpisodeFormattingToken.ABSOLUTE_EPISODE_NUMBER.value: "Absolute Episode Number",
    EpisodeFormattingToken.EPISODE_TITLE.value: "Episode Title",
    EpisodeFormattingToken.ENCODING.value: "Encoding",
    EpisodeFormattingToken.RESOLUTION.value: "Resolution",
    EpisodeFormattingToken.RELEASE_GROUP.value: "Release Group",
}


QBITTORRENT_UNFINISHED_STATES = {"allocating", "downloading", "metaDL", "pausedDL", "queuedDL", "stalledDL",
                                 "checkingDL", "forcedDL", "checkingResumeData", "moving", "unknown"}
QBITTORRENT_ERROR_STATES = {"error", "missingFiles"}
