import json
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, UTC

# noinspection PyPackageRequirements
import pymysql

from common.context_helpers import thread_out
from common.exceptions import ObjectNotFoundException, InvalidBackupException
from components import BaseComponent
from config import config
from dto.app_version import AppVersion
from utils.helpers.backup_helpers import validate_backup_archive

BACKUP_TABLES = (
    'settings',
    'tracked_anime_profile',
    'tracked_anime',
    'tracked_anime_processing_settings',
    'tracked_anime_release_group_preferences',
    'tracked_anime_episode',
    'torrent',
    'torrent_download',
    'mapping_override',
    'notification',
    'audit_log',
)

BACKUP_FILES = (
    'release_groups_custom.json',
)

MIGRATION_SEEDED_TABLES = (
    'settings',
    'tracked_anime_profile',
)

USER_BACKUP_PREFIX = "user-backup-"
AUTO_BACKUP_PREFIX = "backup-"
AUTO_BACKUP_RETENTION_COUNT = 14

_INSERT_BATCH_SIZE = 500


@dataclass
class BackupInfo:
    filename: str
    path: str
    created_at: datetime
    size_bytes: int
    app_version: str
    schema_version: str
    tables: dict[str, int]  # table name:: row count
    files: list[str]

    @property
    def can_restore(self) -> bool:
        # noinspection PyDataclass
        return AppVersion.from_string(self.schema_version) <= config.app_version.as_core()


class BackupComponent(BaseComponent):

    @property
    def _backups_dir(self) -> str:
        return os.path.join(config.data_dir, "backups")

    @property
    def _restore_marker_path(self) -> str:
        return os.path.join(self._backups_dir, ".pending_restore")

    async def create_backup(self, user_initiated: bool = False) -> BackupInfo:
        os.makedirs(self._backups_dir, exist_ok=True)
        backup_info = await thread_out(self._create_backup_sync, user_initiated)
        self.logger.info(f"Created backup {backup_info.filename} "
                         f"({sum(backup_info.tables.values())} rows, {backup_info.size_bytes} bytes).")
        return backup_info

    def _create_backup_sync(self, user_initiated: bool) -> BackupInfo:
        created_at = datetime.now(UTC)
        prefix = USER_BACKUP_PREFIX if user_initiated else AUTO_BACKUP_PREFIX
        filename = f"{prefix}{created_at.strftime('%Y-%m-%dT%H-%M-%SZ')}.zip"
        archive_path = os.path.join(self._backups_dir, filename)

        staging_dir = tempfile.mkdtemp(prefix="saberr-backup-")
        try:
            schema_version, table_row_counts = self._export_tables(staging_dir=staging_dir)
            included_files = self._copy_data_files(staging_dir=staging_dir)

            manifest = {
                "created_at": created_at.isoformat(),
                "app_version": config.app_version.original_version_string,
                "schema_version": schema_version,
                "tables": table_row_counts,
                "files": included_files,
            }
            with open(os.path.join(staging_dir, "manifest.json"), "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=4)

            self._zip_dir(source_dir=staging_dir, archive_path=archive_path)
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

        return BackupInfo(
            filename=filename,
            path=archive_path,
            created_at=created_at,
            size_bytes=os.path.getsize(archive_path),
            app_version=config.app_version.original_version_string,
            schema_version=schema_version,
            tables=table_row_counts,
            files=included_files,
        )

    def _export_tables(self, staging_dir: str) -> tuple[str, dict[str, int]]:
        conn = pymysql.connect(
            host=config.db_host,
            port=config.db_port,
            user=config.db_user,
            password=config.db_password,
            database=config.db_name,
            charset="utf8mb4",
            connect_timeout=5,
        )
        try:
            cursor = conn.cursor()
            cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT;")
            schema_version = self._read_schema_version(cursor)

            table_row_counts: dict[str, int] = {}
            with open(os.path.join(staging_dir, "db.sql"), "w", encoding="utf-8", newline="\n") as sql_file:
                sql_file.write("SET FOREIGN_KEY_CHECKS=0;\n")
                for table in BACKUP_TABLES:
                    table_row_counts[table] = self._export_table(conn=conn, cursor=cursor,
                                                                 table=table, sql_file=sql_file)
                sql_file.write("SET FOREIGN_KEY_CHECKS=1;\n")
            conn.commit()
            return schema_version, table_row_counts
        finally:
            conn.close()

    @staticmethod
    def _export_table(conn, cursor, table: str, sql_file) -> int:
        cursor.execute(f"SELECT * FROM `{table}`;")
        columns = [desc[0] for desc in cursor.description]

        included_indexes = list(range(len(columns)))
        if table == 'settings':
            included_indexes = [index for index, column in enumerate(columns) if column != 'id']
        included_columns = [columns[index] for index in included_indexes]
        col_list = ", ".join(f"`{column}`" for column in included_columns)

        on_conflict = ""
        if table in MIGRATION_SEEDED_TABLES:
            updates = ", ".join(f"`{column}`=VALUES(`{column}`)" for column in included_columns)
            on_conflict = f"\nON DUPLICATE KEY UPDATE {updates}"

        row_count = 0
        while batch := cursor.fetchmany(_INSERT_BATCH_SIZE):
            row_count += len(batch)
            values_sql = ",\n".join(
                "(" + ", ".join(conn.escape(row[index]) for index in included_indexes) + ")"
                for row in batch
            )
            sql_file.write(f"INSERT INTO `{table}` ({col_list}) VALUES\n{values_sql}{on_conflict};\n")
        return row_count

    @staticmethod
    def _read_schema_version(cursor) -> str:
        cursor.execute("SELECT data FROM saberr_metadata WHERE code = 'db_schema_metadata';")
        row = cursor.fetchone()
        if not row:
            raise Exception("Failed to read schema version, cannot create backup.")
        try:
            return json.loads(row[0])['version']
        except Exception as e:
            raise Exception(f"Failed to read schema version: {e}") from e

    @staticmethod
    def _copy_data_files(staging_dir: str) -> list[str]:
        included_files = []
        for relative_path in BACKUP_FILES:
            source_path = os.path.join(config.data_dir, relative_path)
            if not os.path.isfile(source_path):
                continue
            target_path = os.path.join(staging_dir, "files", relative_path)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(source_path, target_path)
            included_files.append(relative_path.replace(os.sep, "/"))
        return included_files

    @staticmethod
    def _zip_dir(source_dir: str, archive_path: str):
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    absolute_path = os.path.join(root, file)
                    archive.write(absolute_path, os.path.relpath(absolute_path, source_dir))

    async def mark_backup_for_restoration(self, filename: str) -> dict:
        archive_path = self._resolve_archive_path(filename)
        manifest = await thread_out(validate_backup_archive, archive_path, config.app_version)
        await thread_out(self._write_restore_marker, filename, manifest)
        self.logger.info(f"Staged backup {filename} for restore on next startup "
                         f"(schema {manifest['schema_version']}).")
        return manifest

    def _resolve_archive_path(self, filename: str) -> str:
        if not filename.endswith(".zip") or os.path.basename(filename) != filename or filename.startswith("."):
            raise InvalidBackupException(f"Invalid backup filename: {filename!r}.")
        archive_path = os.path.join(self._backups_dir, filename)
        if not os.path.isfile(archive_path):
            raise ObjectNotFoundException(f"Backup {filename!r} not found.")
        return archive_path

    def _write_restore_marker(self, filename: str, manifest: dict):
        marker = {
            "filename": filename,
            "schema_version": manifest["schema_version"],
            "requested_at": datetime.now(UTC).isoformat(),
        }
        with open(self._restore_marker_path, "w", encoding="utf-8") as f:
            json.dump(marker, f, indent=4)

    async def list_backups(self) -> list[BackupInfo]:
        return await thread_out(self._list_backups_sync)

    def _list_backups_sync(self) -> list[BackupInfo]:
        if not os.path.isdir(self._backups_dir):
            return []
        backups = []
        for filename in os.listdir(self._backups_dir):
            if not filename.endswith(".zip"):
                continue
            archive_path = os.path.join(self._backups_dir, filename)
            try:
                manifest = self._read_manifest(archive_path)
            except InvalidBackupException as e:
                self.logger.warning(f"Skipping unreadable backup {filename}: {e}")
                continue
            backups.append(BackupInfo(
                filename=filename,
                path=archive_path,
                created_at=datetime.fromisoformat(manifest["created_at"]),
                size_bytes=os.path.getsize(archive_path),
                app_version=manifest["app_version"],
                schema_version=manifest["schema_version"],
                tables=manifest["tables"],
                files=manifest["files"],
            ))
        return sorted(backups, key=lambda backup: backup.created_at, reverse=True)

    async def delete_backup(self, filename: str):
        archive_path = self._resolve_archive_path(filename)
        await thread_out(os.remove, archive_path)
        self.logger.info(f"Deleted backup {filename}.")

    async def prune_old_backups(self):
        await thread_out(self._prune_old_backups_sync)

    def _prune_old_backups_sync(self):
        if not os.path.isdir(self._backups_dir):
            return
        auto_backups = sorted(
            (filename for filename in os.listdir(self._backups_dir)
             if filename.endswith(".zip") and not filename.startswith(USER_BACKUP_PREFIX)),
            reverse=True,
        )
        for filename in auto_backups[AUTO_BACKUP_RETENTION_COUNT:]:
            os.remove(os.path.join(self._backups_dir, filename))
            self.logger.info(f"Pruned old backup {filename}.")

    @staticmethod
    def _read_manifest(archive_path: str) -> dict:
        try:
            with zipfile.ZipFile(archive_path) as archive:
                with archive.open("manifest.json") as manifest_file:
                    return json.load(manifest_file)
        except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as e:
            raise InvalidBackupException(f"Unreadable backup archive: {e}") from e
