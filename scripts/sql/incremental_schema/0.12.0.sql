INSERT IGNORE INTO settings (code, data)
VALUES ('RSS_PROXY_CONFIG',
        NULL); -- str when filled

INSERT IGNORE INTO settings (code, data)
VALUES ('RSS_PROXY_TORRENT_FILES_ENABLED',
        'true');

UPDATE `saberr_metadata`
SET `data` = JSON_SET(`data`, '$.version', '0.12.0')
WHERE `code` = 'db_schema_metadata';