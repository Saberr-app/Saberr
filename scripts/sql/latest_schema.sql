-- ##### TABLE: anilist_anime #####

CREATE TABLE IF NOT EXISTS anilist_anime
(
    id          INT AUTO_INCREMENT PRIMARY KEY,
    anilist_id  INT  NOT NULL UNIQUE,
    data        JSON NOT NULL,
    search_blob TEXT AS (CONCAT_WS(' | ', JSON_VALUE(data, '$.title.romaji'), JSON_VALUE(data, '$.title.english'),
                                   JSON_VALUE(data, '$.title.native'), REPLACE(REPLACE(REPLACE(REPLACE(
                                                                                                       JSON_UNQUOTE(JSON_EXTRACT(data, '$.synonyms')),
                                                                                                       '", "', ' | '),
                                                                                               '["', '| '), '"]', ''),
                                                                               '[]', ''))) STORED,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FULLTEXT INDEX anilist_anime_search_blob_idx (search_blob)
) COLLATE = utf8mb4_general_ci;

-- ##### TABLE: anilist_anime_extras #####

CREATE TABLE IF NOT EXISTS anilist_anime_extras
(
    id         INT AUTO_INCREMENT PRIMARY KEY,
    anilist_id INT  NOT NULL UNIQUE,
    data       JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COLLATE = utf8mb4_general_ci;

-- ##### TABLE: anilist_anime_airing_schedule #####

CREATE TABLE IF NOT EXISTS anilist_anime_airing_schedule
(
    id         INT AUTO_INCREMENT PRIMARY KEY,
    anilist_id INT NOT NULL,
    episode    INT NOT NULL,
    airing_at  INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE (anilist_id, episode)
) COLLATE = utf8mb4_general_ci;

-- ##### TABLE: anilist_anime_monthly_airing_schedule #####

CREATE TABLE IF NOT EXISTS anilist_anime_monthly_airing_schedule
(
    id         INT AUTO_INCREMENT PRIMARY KEY,
    anilist_id INT      NOT NULL,
    month      DATETIME NOT NULL, -- as the first day of the month
    data       JSON     NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE (anilist_id, month)
) COLLATE = utf8mb4_general_ci;

-- ##### TABLE: tvdb_series #####

CREATE TABLE IF NOT EXISTS tvdb_series
(
    id             INT AUTO_INCREMENT PRIMARY KEY,
    tvdb_series_id INT  NOT NULL UNIQUE,
    data           JSON NOT NULL,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COLLATE = utf8mb4_general_ci;

-- ##### TABLE: tvdb_series_episodes #####

CREATE TABLE IF NOT EXISTS tvdb_series_episodes
(
    id             INT AUTO_INCREMENT PRIMARY KEY,
    tvdb_series_id INT                                                           NOT NULL,
    season_type    ENUM ('official', 'absolute', 'dvd', 'alternate', 'regional') NOT NULL,
    data           JSON                                                          NOT NULL,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE (tvdb_series_id, season_type)
) COLLATE = utf8mb4_general_ci;

-- ##### TABLE: anilist_list_item #####

CREATE TABLE IF NOT EXISTS anilist_list_item
(
    id         INT AUTO_INCREMENT PRIMARY KEY,
    anilist_id INT  NOT NULL UNIQUE,
    data       JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COLLATE = utf8mb4_general_ci;

-- ##### TABLE: settings #####

CREATE TABLE IF NOT EXISTS settings
(
    id         INT AUTO_INCREMENT PRIMARY KEY,
    code       TEXT NOT NULL UNIQUE,
    data       TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COLLATE = utf8mb4_general_ci;

-- ##### TABLE: tracked_anime_profile #####

CREATE TABLE IF NOT EXISTS tracked_anime_profile
(
    id                        INT AUTO_INCREMENT PRIMARY KEY,
    preferred_release_groups  JSON    NOT NULL,           -- inherently restrictive
    preferred_encodings       JSON    NOT NULL,           -- inherently restrictive
    preferred_resolutions     JSON    NOT NULL,           -- inherently restrictive
    preferred_language_codes  JSON    NOT NULL,
    preferred_sources         JSON    NOT NULL,
    language_codes_restricted TINYINT NOT NULL DEFAULT 0, -- whether to restrict to only the preferred language codes
    sources_restricted        TINYINT NOT NULL DEFAULT 0, -- whether to restrict to only the preferred sources
    accept_release_upgrades   TINYINT NOT NULL DEFAULT 1,
    priorities_sorted         JSON    NOT NULL,           -- list of criteria in order of importance, e.g. [resolution, language_code, release_group, source, version, encoding]
    created_at                DATETIME         DEFAULT CURRENT_TIMESTAMP,
    updated_at                DATETIME         DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COLLATE = utf8mb4_general_ci;

-- create a default profile
INSERT IGNORE INTO tracked_anime_profile (id, preferred_release_groups, preferred_encodings,
                                          preferred_resolutions, preferred_language_codes, preferred_sources,
                                          language_codes_restricted, sources_restricted, priorities_sorted)
VALUES (1,
        '[
            "Erai-raws",
            "DKB",
            "Judas"
        ]',
        '[
            "HEVC",
            "AV1",
            "AVC"
        ]',
        '[
            "1080p"
        ]',
        '[
            "JP",
            "CN",
            "EN"
        ]',
        '[]',
        1,
        0,
        '[
            "resolution",
            "language_code",
            "release_group",
            "source",
            "version",
            "encoding"
        ]');

-- ##### TABLE: tracked_anime #####

CREATE TABLE IF NOT EXISTS tracked_anime
(
    id                       INT AUTO_INCREMENT PRIMARY KEY,
    tracked_anime_profile_id INT                                                           NOT NULL DEFAULT 1,
    romaji_title             TEXT                                                          NOT NULL,
    native_title             TEXT                                                          NULL,
    english_title            TEXT                                                          NULL,
    anilist_id               INT                                                           NOT NULL UNIQUE,
    status                   ENUM ('ACTIVE', 'ARCHIVED')                                   NOT NULL,
    from_episode             INT                                                           NOT NULL DEFAULT 1,
    tvdb_structure_enabled   TINYINT                                                       NOT NULL DEFAULT 0,
    tvdb_season_type         ENUM ('official', 'absolute', 'dvd', 'alternate', 'regional') NOT NULL DEFAULT 'official',
    show_parent_directory    TEXT                                                          NOT NULL,
    show_folder_name         TEXT                                                          NOT NULL,
    created_at               DATETIME                                                               DEFAULT CURRENT_TIMESTAMP,
    updated_at               DATETIME                                                               DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tracked_anime_profile_id) REFERENCES tracked_anime_profile (id) ON UPDATE CASCADE ON DELETE RESTRICT
) COLLATE = utf8mb4_general_ci;

-- ##### TABLE: tracked_anime_processing_settings #####

CREATE TABLE IF NOT EXISTS tracked_anime_processing_settings
(
    id                                 INT AUTO_INCREMENT PRIMARY KEY,
    tracked_anime_id                   INT  NOT NULL UNIQUE,
    episode_number_padding             INT  NOT NULL DEFAULT 2,
    season_number_padding              INT  NOT NULL DEFAULT 2, -- tvdb structuring must be enabled
    season_directory_number_padding    INT  NOT NULL DEFAULT 1, -- tvdb structuring must be enabled
    season_directory_name_format       TEXT NOT NULL,           -- tvdb structuring must be enabled
    raw_episode_file_name_format       TEXT NOT NULL,           -- if tvdb structuring is disabled
    episode_file_name_format           TEXT NOT NULL,           -- tvdb structuring must be enabled
    titleless_episode_file_name_format TEXT NOT NULL,           -- tvdb structuring must be enabled
    created_at                         DATETIME      DEFAULT CURRENT_TIMESTAMP,
    updated_at                         DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tracked_anime_id) REFERENCES tracked_anime (id) ON UPDATE CASCADE ON DELETE CASCADE
) COLLATE = utf8mb4_general_ci;

-- ##### TABLE: tracked_anime_release_group_preferences #####

CREATE TABLE IF NOT EXISTS tracked_anime_release_group_preferences
(
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    tracked_anime_id       INT  NOT NULL,
    release_group          TEXT NOT NULL,
    episode_number_offset  INT  NOT NULL DEFAULT 0, -- pos/neg, only effective if override_match_against is set and used
    override_match_against TEXT NULL,               -- title to catch in torrent name
    created_at             DATETIME      DEFAULT CURRENT_TIMESTAMP,
    updated_at             DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tracked_anime_id) REFERENCES tracked_anime (id) ON UPDATE CASCADE ON DELETE CASCADE,
    UNIQUE (tracked_anime_id, release_group)
) COLLATE = utf8mb4_general_ci;

-- ##### TABLE: tracked_anime_episode #####

CREATE TABLE IF NOT EXISTS tracked_anime_episode
(
    id                        INT AUTO_INCREMENT PRIMARY KEY,
    tracked_anime_id          INT     NOT NULL,
    episode_number            INT     NOT NULL,
    tvdb_series_id            INT     NULL,
    tvdb_season_number        INT     NULL,
    tvdb_episode_numbers      JSON    NOT NULL DEFAULT '[]',
    tvdb_episode_ids          JSON    NOT NULL DEFAULT '[]',
    tvdb_episode_part         INT     NULL,               -- only effective if there's one tvdb episode, and the anime episode is only part of it
    tvdb_episode_part_ceiling INT     NULL,               -- the upper bound of the episode part (inclusive)
    auto_discard              TINYINT NOT NULL DEFAULT 0, -- whether to skip this episode in auto selection
    created_at                DATETIME         DEFAULT CURRENT_TIMESTAMP,
    updated_at                DATETIME         DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tracked_anime_id) REFERENCES tracked_anime (id) ON UPDATE CASCADE ON DELETE CASCADE,
    UNIQUE (tracked_anime_id, episode_number)
) COLLATE = utf8mb4_general_ci;

CREATE INDEX idx_tracked_anime_episode_tvdb_series_id ON tracked_anime_episode (tvdb_series_id);

-- ##### TABLE: torrent #####

CREATE TABLE IF NOT EXISTS torrent
(
    id                       INT AUTO_INCREMENT PRIMARY KEY,
    magnet_hash              TEXT                                                                                                     NOT NULL,
    tracked_anime_episode_id INT                                                                                                      NOT NULL,
    parent_torrent_id        INT                                                                                                      NULL,               -- for linking multiple torrent records of the same hash that serve multiple episodes
    rss_xml                  TEXT                                                                                                     NOT NULL,
    torrent_link             TEXT                                                                                                     NOT NULL,
    torrent_title            TEXT                                                                                                     NOT NULL,
    override                 TINYINT                                                                                                  NOT NULL DEFAULT 0,
    discarded                TINYINT                                                                                                  NOT NULL DEFAULT 0, -- set by episode's auto_discard and torrent download delete action
    release_group            TEXT                                                                                                     NOT NULL,
    title                    TEXT                                                                                                     NOT NULL,
    episode_number           INT                                                                                                      NOT NULL,           -- as-is episode number parsed from torrent title, can be different from tracked_anime_episode.episode_number
    episode_part             INT                                                                                                      NOT NULL DEFAULT 0, -- for episodes that are released in multiple parts (e.g. some OVAs), 0 indicates non-partial
    episode_part_ceiling     INT                                                                                                      NOT NULL DEFAULT 0, -- the upper bound of the episode part, only effective if episode_part is not 0, must be >= episode_part
    language_code            TEXT                                                                                                     NOT NULL DEFAULT 'und',
    encoding                 ENUM ('HEVC', 'AVC', 'AV1')                                                                              NOT NULL,
    resolution               ENUM ('480p', '540p', '720p', '1080p', '2160p')                                                          NOT NULL,
    version_number           INT                                                                                                      NOT NULL DEFAULT 1,
    repack_indicator         TINYINT                                                                                                  NOT NULL DEFAULT 0,
    source                   ENUM ('Crunchyroll', 'Netflix', 'Amazon', 'Disney+', 'Anime Digital Network', 'HIDIVE', 'Hulu', 'Other') NOT NULL DEFAULT 'Other',
    created_at               DATETIME                                                                                                          DEFAULT CURRENT_TIMESTAMP,
    updated_at               DATETIME                                                                                                          DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tracked_anime_episode_id) REFERENCES tracked_anime_episode (id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (parent_torrent_id) REFERENCES torrent (id) ON UPDATE CASCADE ON DELETE SET NULL,
    UNIQUE (magnet_hash, tracked_anime_episode_id)
) COLLATE = utf8mb4_general_ci;

CREATE INDEX idx_torrent_tracked_anime_episode_id ON torrent (tracked_anime_episode_id);

-- ##### TABLE: torrent_download #####

CREATE TABLE IF NOT EXISTS torrent_download
(
    id                            INT AUTO_INCREMENT PRIMARY KEY,
    torrent_id                    INT                                                                                                                                                              NOT NULL UNIQUE,
    status                        ENUM ('PENDING', 'DOWNLOADING', 'DOWNLOADED', 'PROCESSING', 'PROCESSED', 'FAILED_DOWNLOAD_INIT', 'FAILED_DOWNLOAD', 'FAILED_PROCESSING', 'DELETED', 'DISCARDED') NOT NULL,
    status_retry_count            INT                                                                                                                                                              NOT NULL DEFAULT 0,
    status_details                TEXT                                                                                                                                                             NULL,
    download_directory_path       TEXT                                                                                                                                                             NULL, -- the determined path for this download to be downloaded into
    source_path                   TEXT                                                                                                                                                             NULL, -- path of the source file
    destination_path              TEXT                                                                                                                                                             NULL, -- the determined path for this download to be processed into, set before processing
    copied_to_destination_path_at DATETIME                                                                                                                                                         NULL, -- helps determine which torrent is the most recent version
    created_at                    DATETIME                                                                                                                                                                  DEFAULT CURRENT_TIMESTAMP,
    updated_at                    DATETIME                                                                                                                                                                  DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (torrent_id) REFERENCES torrent (id) ON UPDATE CASCADE ON DELETE CASCADE
) COLLATE = utf8mb4_general_ci;

-- ##### TABLE: mapping_override #####

CREATE TABLE IF NOT EXISTS mapping_override
(
    id                          INT AUTO_INCREMENT PRIMARY KEY,
    anilist_id                  INT                           NOT NULL,
    anilist_episode_number_from INT                           NOT NULL,
    anilist_episode_number_to   INT                           NULL,
    tvdb_series_id              INT                           NOT NULL,
    tvdb_season_number          INT                           NOT NULL,
    tvdb_episode_number_from    INT                           NOT NULL,
    tvdb_episode_number_to      INT                           NULL,
    granularity                 INT                           NOT NULL DEFAULT 1,
    mode                        ENUM ('IF_MISSING', 'ALWAYS') NOT NULL,
    created_at                  DATETIME                               DEFAULT CURRENT_TIMESTAMP,
    updated_at                  DATETIME                               DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COLLATE = utf8mb4_general_ci;

-- ##### TABLE: notification #####

CREATE TABLE IF NOT EXISTS notification
(
    id           INT AUTO_INCREMENT PRIMARY KEY,
    code         TEXT                              NOT NULL,
    level        ENUM ('INFO', 'WARNING', 'ERROR') NOT NULL,
    text         TEXT                              NOT NULL,
    identifier   JSON                              NULL, -- json identifier relevant to notification code (necessary for marking as stale)
    status       ENUM ('UNREAD', 'READ', 'STALE')  NOT NULL,
    effective_at DATETIME                          NULL, -- snooze-able notifications
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COLLATE = utf8mb4_general_ci;

-- ##### TABLE: audit_log #####

CREATE TABLE IF NOT EXISTS audit_log
(
    id         INT AUTO_INCREMENT PRIMARY KEY,
    code       TEXT                                                                                                                                  NOT NULL,
    category   ENUM ('APP', 'MAPPING_OVERRIDES', 'TORRENT_SELECTION', 'TORRENT_PROCESSING', 'TRACKED_ANIME', 'ANILIST', 'EXTERNAL_SERVICE', 'OTHER') NOT NULL,
    text       TEXT                                                                                                                                  NOT NULL,
    data       JSON                                                                                                                                  NOT NULL,
    context_id TEXT                                                                                                                                  NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COLLATE = utf8mb4_general_ci;

-- ##### TABLE: saberr_metadata #####

CREATE TABLE IF NOT EXISTS saberr_metadata
(
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,
    data JSON NOT NULL
) COLLATE = utf8mb4_general_ci;
INSERT IGNORE INTO saberr_metadata (name, code, data)
VALUES ('DB Schema metadata', 'db_schema_metadata', '{
    "version": "0.1.0"
}');


-- ##### TABLE: cached_asset #####

CREATE TABLE IF NOT EXISTS cached_asset
(
    id             INT AUTO_INCREMENT PRIMARY KEY,
    asset_filename TEXT                        NOT NULL UNIQUE,
    asset_type     ENUM ('relations', 'other') NOT NULL,
    remote         TEXT                        NOT NULL UNIQUE,
    remote_type    ENUM ('URL', 'SCRIPT')      NOT NULL,
    expires_at     DATETIME                    NULL,
    deletable      TINYINT                     NOT NULL DEFAULT 1,
    created_at     DATETIME                             DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME                             DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE (asset_filename, asset_type)
) COLLATE = utf8mb4_general_ci;

INSERT IGNORE INTO cached_asset (asset_filename, asset_type, remote, remote_type, expires_at, deletable)
VALUES ('anime-relations.txt',
        'relations',
        'https://raw.githubusercontent.com/erengy/anime-relations/refs/heads/master/anime-relations.txt',
        'URL',
        CURRENT_TIMESTAMP,
        0),
       ('mappings.min.json',
        'relations',
        'https://github.com/anibridge/anibridge-mappings/releases/download/v3/mappings.min.json',
        'URL',
        CURRENT_TIMESTAMP,
        0),
       ('anime-relations-anilist-episode-count.txt',
        'relations',
        'refresh_anilist_episode_count',
        'SCRIPT',
        CURRENT_TIMESTAMP,
        0);

-- ##### settings default values #####

INSERT IGNORE INTO settings (code, data)
VALUES ('ANILIST_USERNAME',
        NULL); -- str when filled
INSERT IGNORE INTO settings (code, data)
VALUES ('ANILIST_USER_TOKEN',
        NULL); -- str when filled
INSERT IGNORE INTO settings (code, data)
VALUES ('ANILIST_USER_DATA',
        NULL); -- json when filled

INSERT IGNORE INTO settings (code, data)
VALUES ('QBIT_BASE_URL',
        NULL); -- str when filled
INSERT IGNORE INTO settings (code, data)
VALUES ('QBIT_USERNAME',
        NULL); -- str when filled
INSERT IGNORE INTO settings (code, data)
VALUES ('QBIT_PASSWORD',
        NULL); -- str when filled
INSERT IGNORE INTO settings (code, data)
VALUES ('QBIT_REMOTE_PATH_MAPPING',
        NULL); -- json list of 2 when filled as [remote-path, local-path]

INSERT IGNORE INTO settings (code, data)
VALUES ('DEFAULT_DESTINATION_DIRECTORY',
        NULL); -- str when filled
INSERT IGNORE INTO settings (code, data)
VALUES ('DEFAULT_SHOW_DIRECTORY_NAME_FORMAT',
        '{tvdb_title_english}');
INSERT IGNORE INTO settings (code, data)
VALUES ('DEFAULT_SEASON_DIRECTORY_NAME_FORMAT',
        'Season {season_number}');
INSERT IGNORE INTO settings (code, data)
VALUES ('DEFAULT_RAW_EPISODE_FILE_NAME_FORMAT',
        '{anilist_title_romaji} - {episode_number}');
INSERT IGNORE INTO settings (code, data)
VALUES ('DEFAULT_EPISODE_FILE_NAME_FORMAT',
        '{tvdb_title_english} - S{season_number}E{episode_number} - {episode_title}');
INSERT IGNORE INTO settings (code, data)
VALUES ('DEFAULT_TITLELESS_EPISODE_FILE_NAME_FORMAT',
        '{tvdb_title_english} - S{season_number}E{episode_number}');

INSERT IGNORE INTO settings (code, data)
VALUES ('TVDB_STRUCTURE_ENABLED_DEFAULT',
        'true');
INSERT IGNORE INTO settings (code, data)
VALUES ('TORRENT_CATEGORY',
        'Seasonal Anime');
INSERT IGNORE INTO settings (code, data)
VALUES ('STAGING_DIRECTORY',
        NULL); -- str when filled
INSERT IGNORE INTO settings (code, data)
VALUES ('ORGANIZE_DOWNLOADS',
        'true');
INSERT IGNORE INTO settings (code, data)
VALUES ('APPLY_RELEASE_GROUP_AS_TORRENT_TAG',
        'true');
INSERT IGNORE INTO settings (code, data)
VALUES ('APPLY_ENCODING_AS_TORRENT_TAG',
        'false');
INSERT IGNORE INTO settings (code, data)
VALUES ('APPLY_RESOLUTION_AS_TORRENT_TAG',
        'false');
INSERT IGNORE INTO settings (code, data)
VALUES ('APPLY_LANGUAGE_CODE_AS_TORRENT_TAG',
        'false');
INSERT IGNORE INTO settings (code, data)
VALUES ('APPLY_ANIME_TITLE_AS_TORRENT_TAG',
        'true');
INSERT IGNORE INTO settings (code, data)
VALUES ('AUTO_DOWNLOAD',
        'true');
INSERT IGNORE INTO settings (code, data)
VALUES ('RSS_CHECK_FREQUENCY',
        '600'); -- in seconds
INSERT IGNORE INTO settings (code, data)
VALUES ('RSS_CATEGORY',
        'English Translated');
INSERT IGNORE INTO settings (code, data)
VALUES ('SET_DOWNLOAD_AS_FAILED_AFTER_MINUTES',
        '180');
INSERT IGNORE INTO settings (code, data)
VALUES ('SET_PROCESSING_AS_FAILED_AFTER_MINUTES',
        '15');
INSERT IGNORE INTO settings (code, data)
VALUES ('NOTIFICATIONS_DISCORD_WEBHOOK_URL',
        NULL); -- str when filled
INSERT IGNORE INTO settings (code, data)
VALUES ('DISCORD_WEBHOOK_USERNAME',
        NULL); -- str when filled
INSERT IGNORE INTO settings (code, data)
VALUES ('DISCORD_WEBHOOK_AVATAR_URL',
        NULL); -- str when filled
INSERT IGNORE INTO settings (code, data)
VALUES ('DISCORD_NOTIFY_ON_LOGIN',
        'false');
INSERT IGNORE INTO settings (code, data)
VALUES ('DISCORD_NOTIFY_ON_DOWNLOAD_PROCESSED',
        'true');
INSERT IGNORE INTO settings (code, data)
VALUES ('DISCORD_NOTIFY_ON_UPGRADE_DOWNLOAD_PROCESSED',
        'false');
INSERT IGNORE INTO settings (code, data)
VALUES ('DISCORD_NOTIFY_ON_DOWNLOAD_FAILED',
        'true');
INSERT IGNORE INTO settings (code, data)
VALUES ('DISCORD_USER_ID',
        NULL); -- str when filled
INSERT IGNORE INTO settings (code, data)
VALUES ('TIMEZONE',
        'UTC');
INSERT IGNORE INTO settings (code, data)
VALUES ('ANILIST_PREFERRED_TITLE_LANGUAGE',
        'Romaji');
INSERT IGNORE INTO settings (code, data)
VALUES ('PUBLISHED_URL',
        NULL); -- str when filled