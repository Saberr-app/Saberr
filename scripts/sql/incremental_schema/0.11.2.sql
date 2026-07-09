INSERT IGNORE INTO settings (code, data)
VALUES ('QBIT_REMOTE_PATH_MAPPING',
        NULL); -- json list of 2 when filled as [remote-path, local-path]

UPDATE `saberr_metadata`
SET `data` = JSON_SET(`data`, '$.version', '0.11.2')
WHERE `code` = 'db_schema_metadata';