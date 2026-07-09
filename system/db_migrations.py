import json
import logging
import os

# noinspection PyPackageRequirements
import pymysql
from pymysql.constants import CLIENT

from dto.app_version import AppVersion

_logger = logging.getLogger(__name__)


def _get_current_schema_version(cursor) -> str:
    cursor.execute("SHOW TABLES LIKE 'saberr_metadata';")
    if cursor.fetchone():
        cursor.execute("SELECT data FROM saberr_metadata WHERE code = 'db_schema_metadata';")
        row = cursor.fetchone()
        if row:
            data = json.loads(row[0])
            return data.get('version', "0.00")
    return "0.00"


def _ensure_database_exists(config, drop_and_recreate: bool = False):
    conn = pymysql.connect(
        host=config.db_host,
        port=config.db_port,
        user=config.db_user,
        password=config.db_password,
        connect_timeout=5,
    )
    cursor = conn.cursor()
    if drop_and_recreate:
        cursor.execute(f"DROP DATABASE IF EXISTS {config.db_name}")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config.db_name} COLLATE utf8mb4_general_ci")
    cursor.close()
    conn.close()


def apply_db_migrations(config, backup_sql_to_restore: str | None, backup_version: str | None):

    _ensure_database_exists(config=config, drop_and_recreate=bool(backup_sql_to_restore))
    backup_version = AppVersion.from_string(backup_version) if backup_version else None

    conn = pymysql.connect(
        host=config.db_host,
        user=config.db_user,
        password=config.db_password,
        database=config.db_name,
        port=config.db_port,
        connect_timeout=5,
        client_flag=CLIENT.MULTI_STATEMENTS
    )
    cursor = conn.cursor()
    current_schema_version = AppVersion.from_string(_get_current_schema_version(cursor))
    if current_schema_version > config.app_version.as_core():
        raise Exception(f"Current database schema version ({current_schema_version}) "
                        f"is higher than the app version ({config.app_version.original_version_string}).")

    sql_dir = os.path.join("scripts", "sql", "incremental_schema")
    try:
        sql_files = sorted((f for f in os.listdir(sql_dir) if f.endswith(".sql")),
                           key=lambda f: AppVersion.from_string(f.removesuffix(".sql")))
    except ValueError:
        raise Exception(f"Invalid migration file name")
    sql_files_to_execute = []

    backup_execution_index = None
    for file in sql_files:
        version = AppVersion.from_string(file.removesuffix(".sql"))
        # noinspection PyTypeChecker,PyDataclass
        if version <= current_schema_version:
            _logger.debug(f"Skipping already applied migration: {file}")
        else:
            with open(os.path.join(sql_dir, file), "r", encoding="utf-8") as f:
                sql_files_to_execute.append((file, f.read()))
        # noinspection PyTypeChecker
        if backup_version and version >= backup_version and backup_execution_index is None:
            backup_execution_index = len(sql_files_to_execute)

    if backup_sql_to_restore:
        if backup_execution_index is None:
            backup_execution_index = len(sql_files_to_execute)
        restore_statements = [statement.strip() for statement in backup_sql_to_restore.replace("\r\n", "\n").split(";\n")]
        restore_entries = [("backup_restoration", statement) for statement in restore_statements if statement]
        sql_files_to_execute[backup_execution_index:backup_execution_index] = restore_entries

    if sql_files_to_execute:
        _logger.info(f"Applying {len(sql_files_to_execute)} database schema migrations(s)...")
        for file, sql_text in sql_files_to_execute:
            cursor.execute(sql_text)
            while cursor.nextset():
                pass
            conn.commit()
            _logger.info(f"Applied {file}")
        _logger.info("Database schema migrations applied.")
    else:
        _logger.info("Database schema is up to date. No migrations to apply.")

    cursor.close()
    conn.close()
