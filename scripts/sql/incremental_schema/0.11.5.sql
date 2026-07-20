UPDATE `cached_asset`
SET `remote` = 'https://raw.githubusercontent.com/Rapptz/anime-relations/refs/heads/master/anime-relations.txt'
WHERE `asset_filename` = 'anime-relations.txt'
  AND `asset_type` = 'relations';
