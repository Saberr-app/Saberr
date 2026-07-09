ALTER TABLE audit_log
    MODIFY category ENUM ('APP', 'MAPPING_OVERRIDES', 'TORRENT_SELECTION', 'TORRENT_PROCESSING', 'TRACKED_ANIME', 'ANILIST', 'EXTERNAL_SERVICE', 'OTHER') NOT NULL;

UPDATE `saberr_metadata`
SET `data` = JSON_SET(`data`, '$.version', '0.11.3')
WHERE `code` = 'db_schema_metadata';