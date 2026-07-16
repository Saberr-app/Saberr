UPDATE `tracked_anime`
SET `show_folder_name` = REGEXP_REPLACE(`show_folder_name`, '[ .]+$', '')
WHERE `show_folder_name` REGEXP '[ .]$';

UPDATE `settings`
SET `data` = REGEXP_REPLACE(`data`, '[ .]+$', '')
WHERE `code` = 'STAGING_DIRECTORY'
  AND `data` REGEXP '[ .]$';


UPDATE `saberr_metadata`
SET `data` = JSON_SET(`data`, '$.version', '0.11.4')
WHERE `code` = 'db_schema_metadata';