INSERT IGNORE INTO settings (code, data)
VALUES ('RSS_PROXY_CONFIG',
        NULL); -- str when filled

INSERT IGNORE INTO settings (code, data)
VALUES ('RSS_PROXY_TORRENT_FILES_ENABLED',
        'true');

INSERT IGNORE INTO settings (code, data)
VALUES ('DISCORD_SEND_DAILY_MISSING_REPORT',
        'false');

INSERT IGNORE INTO settings (code, data)
VALUES ('HOT_MAPPING_OVERRIDES_ENABLED',
        'true');

UPDATE `settings`
SET `data` = 'Saberr'
WHERE `code` = 'DISCORD_WEBHOOK_USERNAME'
  AND `data` IS NULL;
UPDATE `settings`
SET `data` = 'https://raw.githubusercontent.com/Saberr-app/Saberr/refs/heads/master/assets/legacy/logo.jpg'
WHERE `code` = 'DISCORD_WEBHOOK_AVATAR_URL'
  AND `data` IS NULL;

INSERT IGNORE INTO cached_asset (asset_filename, asset_type, remote, remote_type, expires_at, deletable)
VALUES ('overrides.min.json',
        'relations',
        'https://raw.githubusercontent.com/Saberr-app/SaberrHotMappings/refs/heads/main/overrides.min.json',
        'URL',
        CURRENT_TIMESTAMP,
        0);

UPDATE `saberr_metadata`
SET `data` = JSON_SET(`data`, '$.version', '0.12.0')
WHERE `code` = 'db_schema_metadata';
