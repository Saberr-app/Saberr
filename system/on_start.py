import os
import json
import base64
import asyncio
import argparse
import secrets
import shutil
import zipfile
import logging
from datetime import datetime, UTC, timedelta

import jsonschema

from constants import AppContext
from dto.app_version import AppVersion
from system.db_migrations import apply_db_migrations
from utils.helpers.backup_helpers import validate_backup_archive
from utils.json_schemas import CONFIG_JSON_SCHEMA

_logger = logging.getLogger(__name__)


def resolve_context():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--CONTEXT")
    args, _ = parser.parse_known_args()
    if args.CONTEXT:
        return args.CONTEXT
    try:
        from build_info import CONTEXT
        return CONTEXT
    except ImportError:
        return AppContext.CONSOLE.value


def load_env_overrides():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--CONTEXT")
    parser.add_argument("--DATA-DIR", dest="DATA_DIR")
    parser.add_argument("--WEB-DIR", dest="WEB_DIR")
    parser.add_argument("--PORT", dest="PORT", type=int)
    parser.add_argument("--LOG-LEVEL", dest="LOG_LEVEL")
    parser.add_argument("--DB-HOST", dest="DB_HOST")
    parser.add_argument("--DB-PORT", dest="DB_PORT", type=int)
    parser.add_argument("--DB-NAME", dest="DB_NAME")
    parser.add_argument("--DB-USER", dest="DB_USER")
    parser.add_argument("--DB-PASS", dest="DB_PASS")
    args, _ = parser.parse_known_args()

    context = resolve_context()
    assert context in AppContext.as_list(), \
        f"Invalid context '{context}', must be one of: {', '.join(AppContext.as_list())}"

    try:
        from build_info import BUILD_NUMBER as build_number  # noqa
    except ImportError:
        build_number = None

    if context == AppContext.WINDOWS.value:
        data_dir = args.DATA_DIR or os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"), "Saberr")
    else:
        data_dir = args.DATA_DIR or "data"

    os.environ["CONTEXT"] = context
    os.environ["DATA_DIR"] = data_dir
    os.environ["WEB_DIR"] = args.WEB_DIR or "web"
    if build_number is not None:
        os.environ["BUILD_NUMBER"] = str(build_number)
    if args.DB_HOST is not None:
        os.environ["DB_HOST"] = str(args.DB_HOST)
    if args.DB_PORT is not None:
        os.environ["DB_PORT"] = str(args.DB_PORT)
    if args.DB_NAME is not None:
        os.environ["DB_NAME"] = str(args.DB_NAME)
    if args.DB_USER is not None:
        os.environ["DB_USER"] = str(args.DB_USER)
    if args.DB_PASS is not None:
        os.environ["DB_PASSWORD"] = str(args.DB_PASS)
    if args.PORT is not None:
        os.environ["PORT"] = str(args.PORT)
    if args.LOG_LEVEL is not None:
        os.environ["LOG_LEVEL"] = str(args.LOG_LEVEL)


def prep_data_dir():
    data_dir = os.environ["DATA_DIR"]
    os.makedirs(data_dir, exist_ok=True)

    default_dir = "data.default"
    for root, _, files in os.walk(default_dir):
        rel_root = os.path.relpath(root, default_dir)
        dest_root = data_dir if rel_root == "." else os.path.join(data_dir, rel_root)
        os.makedirs(dest_root, exist_ok=True)
        for file_name in files:
            source = os.path.join(root, file_name)
            destination = os.path.join(dest_root, file_name)
            if os.path.exists(destination):
                continue
            shutil.copy2(source, destination)
            _logger.debug(f"Copied missing data file: {source} -> {destination}")
    # release_groups.json should always overwrite for potential updates
    shutil.copy2(os.path.join(default_dir, "release_groups.json"), os.path.join(data_dir, "release_groups.json"))
    _logger.debug(f"Copied default release groups file.")

    if os.environ["CONTEXT"] == AppContext.WINDOWS.value:
        if not os.path.exists(os.path.join(data_dir, "config", "config.json")):
            os.makedirs(os.path.join(data_dir, "config"), exist_ok=True)
            config_path = os.path.join(data_dir, "config", "config.json")
            jwt_secret_b64 = base64.b64encode(secrets.token_hex(32).encode("utf-8")).decode("ascii")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "port": int(os.environ["PORT"]) if os.environ.get("PORT") else 8125,
                        "log_level": os.environ.get("LOG_LEVEL") or "INFO",
                        "db": {
                            "host": os.environ.get("DB_HOST") or "localhost",
                            "port": int(os.environ["DB_PORT"]) if os.environ.get("DB_PORT") else 5798,
                            "name": os.environ.get("DB_NAME") or "saberr",
                            "user": os.environ.get("DB_USER") or "saberr",
                            "password": os.environ.get("DB_PASSWORD") or "saberr",
                        },
                        "credentials": {
                            "username": "",
                            "password": "",
                            "jwt_secret": jwt_secret_b64
                        },
                        "networking": {
                            "allow_all_origins": False,
                            "proxy_external_images": False
                        }
                    },
                    f, indent=4, ensure_ascii=False
                )
            _logger.info(f"Generated default config file at {config_path}")


def load_context_specific_env():
    context = os.environ["CONTEXT"]
    if context == AppContext.WINDOWS.value:
        data_dir = os.environ["DATA_DIR"]

        config_path = os.path.join(data_dir, "config", "config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_json = json.load(f)
            jsonschema.validate(config_json, CONFIG_JSON_SCHEMA)
        except FileNotFoundError:
            _logger.error(f"Config file not found at {config_path}")
            exit(1)
        except json.JSONDecodeError as e:
            _logger.error(f"Invalid config file ({e}): {config_path}")
            exit(1)
        except jsonschema.ValidationError as e:
            _logger.error(f"Config file validation error ({e}): {config_path}")
            exit(1)
        except Exception as e:
            _logger.error(f"Unexpected error loading config file ({e}): {config_path}")
            exit(1)

        credentials = config_json["credentials"]
        db = config_json["db"]
        networking = config_json["networking"]

        os.environ["ADMIN_USERNAME"] = credentials["username"]
        os.environ["ADMIN_PASSWORD_HASH"] = credentials["password"]
        try:
            os.environ["JWT_SECRET"] = base64.b64decode(credentials["jwt_secret"]).decode("utf-8")
        except Exception as e:
            _logger.error(f"Failed to decode JWT secret from config file ({e}): {config_path}")
            exit(1)
        if os.environ.get("PORT") is None:
            os.environ["PORT"] = str(config_json["port"])
        if os.environ.get("LOG_LEVEL") is None:
            os.environ["LOG_LEVEL"] = config_json["log_level"]
        if os.environ.get("DB_HOST") is None:
            os.environ["DB_HOST"] = db["host"]
        if os.environ.get("DB_PORT") is None:
            os.environ["DB_PORT"] = str(db["port"])
        if os.environ.get("DB_NAME") is None:
            os.environ["DB_NAME"] = db["name"]
        if os.environ.get("DB_USER") is None:
            os.environ["DB_USER"] = db["user"]
        if os.environ.get("DB_PASSWORD") is None:
            os.environ["DB_PASSWORD"] = db["password"]
        os.environ["ALLOW_ALL_ORIGINS"] = str(networking["allow_all_origins"]).lower()
        os.environ["PROXY_EXTERNAL_IMAGES"] = str(networking["proxy_external_images"]).lower()
        os.environ["SQL_ECHO"] = "false"
        os.environ["DEBUG"] = "false"

        logging.getLogger().setLevel(os.environ["LOG_LEVEL"].upper())


def restore_backup(config):
    backup_dir = os.path.join(config.data_dir, "backups")
    restore_marker_path = os.path.join(backup_dir, ".pending_restore")
    if not os.path.exists(restore_marker_path):
        return None, None, None
    try:
        with open(restore_marker_path, "r", encoding="utf-8") as f:
            restore_data = json.load(f)
        filename = restore_data["filename"]
        schema_version = restore_data["schema_version"]
        requested_at = datetime.fromisoformat(restore_data["requested_at"]).astimezone(UTC)
    except Exception as e:
        _logger.error(f"Invalid restore marker file, skipping restore: {e}")
        os.remove(restore_marker_path)
        return None, None, None
    if (datetime.now(UTC) - requested_at) > timedelta(hours=3):
        _logger.error(f"Restore marker file is too old, skipping restore")
        os.remove(restore_marker_path)
        return None, None, None
    if config.app_version.as_core() < AppVersion.from_string(schema_version):
        _logger.error(f"Backup schema version is newer than current version, skipping restore")
        os.remove(restore_marker_path)
        return None, None, None
    backup_path = os.path.join(backup_dir, filename)
    if not os.path.exists(backup_path):
        _logger.error(f"Backup file not found, skipping restore")
        os.remove(restore_marker_path)
        return None, None, None
    try:
        manifest = validate_backup_archive(backup_path, app_version=config.app_version)
    except Exception as e:
        _logger.error(f"Invalid backup archive, skipping restore: {e}")
        os.remove(restore_marker_path)
        return None, None, None

    try:
        with zipfile.ZipFile(backup_path) as archive:
            archive_members = set(archive.namelist())
            custom_groups_member = "files/release_groups_custom.json"
            if custom_groups_member in archive_members:
                custom_groups_path = os.path.join(config.data_dir, "release_groups_custom.json")
                with archive.open(custom_groups_member) as source, open(custom_groups_path, "wb") as destination:
                    shutil.copyfileobj(source,
                                       destination)  # noqa
                _logger.info("Restored release_groups_custom.json from backup.")
            backup_sql_to_restore = archive.read("db.sql").decode("utf-8")
    except Exception as e:
        _logger.error(f"Failed to read backup archive, skipping restore: {e}")
        os.remove(restore_marker_path)
        return None, None, None

    return backup_sql_to_restore, manifest["schema_version"], restore_marker_path


def init_db(config, backup_sql_to_restore, backup_version):
    try:
        apply_db_migrations(config, backup_sql_to_restore, backup_version)
    except Exception as e:
        _logger.exception(f"Failed to apply database migrations: {e}")
        exit(1)


async def load_app_settings(config):
    from common.db import session_context, engine
    from repositories.settings_repo import SettingsRepo
    from dto.settings import UserSettings

    try:
        async with session_context() as session:
            repo = SettingsRepo(session)
            settings_records = await repo.get_all_settings()
            code_data_map = {record.code.value: record.data for record in settings_records}
            config.user_settings = UserSettings.from_dict(code_data_map)
    except Exception as e:
        _logger.exception(f"Failed to load app settings: {e}")
        exit(1)

    # solves the issue of the uvicorn loop reusing this loop's connection and failing
    # because this loop had already been destroyed
    await engine.dispose()


def on_start_actions():
    load_env_overrides()
    from common.logging_config import setup_logging
    setup_logging("saberr.log")
    prep_data_dir()
    load_context_specific_env()
    from config import config
    backup_sql_to_restore, backup_version, restore_marker_path = restore_backup(config)
    init_db(config, backup_sql_to_restore, backup_version)
    if restore_marker_path:
        os.remove(restore_marker_path)
    asyncio.run(load_app_settings(config))
