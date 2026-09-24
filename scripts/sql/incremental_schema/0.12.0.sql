INSERT IGNORE INTO settings (code, data)
VALUES ('DISCORD_SEND_DAILY_MISSING_REPORT',
        'false');

UPDATE `saberr_metadata`
SET `data` = JSON_SET(`data`, '$.version', '0.12.0')
WHERE `code` = 'db_schema_metadata';