INSERT IGNORE INTO settings (code, data)
VALUES ('HOT_MAPPING_OVERRIDES_ENABLED',
        'true');

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