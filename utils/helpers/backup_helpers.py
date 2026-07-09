import json
import zipfile

from common.exceptions import InvalidBackupException
from dto.app_version import AppVersion


def validate_backup_archive(archive_path: str, app_version: AppVersion) -> dict:
    try:
        with zipfile.ZipFile(archive_path) as archive:
            if archive.testzip() is not None:
                raise InvalidBackupException("Backup archive is corrupt.")
            with archive.open("manifest.json") as manifest_file:
                manifest = json.load(manifest_file)
            names = set(archive.namelist())
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as e:
        raise InvalidBackupException(f"Unreadable backup archive: {e}") from e

    required_keys = {"app_version", "schema_version", "tables", "files"}
    if not required_keys.issubset(manifest):
        raise InvalidBackupException("Backup manifest is missing required fields.")

    try:
        if AppVersion.from_string(manifest["schema_version"]) > app_version.as_core():
            raise InvalidBackupException(f"Backup schema version {manifest['schema_version']} is newer "
                                         f"than this app's version {app_version.original_version_string}.")
    except ValueError as e:
        raise InvalidBackupException(f"Invalid schema version in backup manifest: {e}") from e

    missing = [member for member in
               ["db.sql"]
               + [f"files/{file}" for file in manifest["files"]]
               if member not in names]
    if missing:
        raise InvalidBackupException(f"Backup archive is missing expected members: {', '.join(missing)}.")

    return manifest
