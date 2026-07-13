__all__ = ['config']

import logging
import os
import json
from dataclasses import dataclass

import jsonschema

from constants import AppContext
from dto.app_version import AppVersion
from dto.settings import ReleaseGroup, UserSettings
from utils.json_schemas import RELEASE_GROUPS_JSON_SCHEMA

logger = logging.getLogger(__name__)


@dataclass
class _Config:
    port: int
    log_level: str

    admin_username: str
    admin_password_hash: str
    jwt_secret: str

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    sql_echo: bool

    debug: bool
    allow_all_origins: bool
    proxy_external_images: bool

    app_version: AppVersion
    ui_minimum_version: AppVersion
    context: AppContext
    build_number: int | None
    data_dir: str
    web_dir: str

    release_groups_map: dict[str, ReleaseGroup]
    user_settings: UserSettings

    @classmethod
    def init(cls):
        try:
            assert os.environ.get("PORT") is not None and os.environ.get("PORT").isdigit(), \
                "PORT environment variable is not set or not a valid integer"
            assert (os.environ.get("LOG_LEVEL") is None
                    or os.environ.get("LOG_LEVEL").lower() in ("debug", "info", "warning", "error", "critical")), \
                "LOG_LEVEL environment variable must be one of: debug, info, warning, error, critical"

            assert os.environ.get("ADMIN_USERNAME") is not None, \
                "ADMIN_USERNAME environment variable is not set"
            assert ((os.environ.get("ADMIN_PASSWORD") is not None)
                    ^ (os.environ.get("ADMIN_PASSWORD_HASH") is not None)), \
                "exactly one of ADMIN_PASSWORD or ADMIN_PASSWORD_HASH must be set"
            assert os.environ.get("JWT_SECRET") is not None, \
                "JWT_SECRET environment variable is not set"

            assert os.environ.get("DB_HOST") is not None, \
                "DB_HOST environment variable is not set"
            assert os.environ.get("DB_PORT") is not None and os.environ.get("DB_PORT").isdigit(), \
                "DB_PORT environment variable is not set or not a valid integer"
            assert os.environ.get("DB_NAME") is not None, \
                "DB_NAME environment variable is not set"
            assert os.environ.get("DB_USER") is not None, \
                "DB_USER environment variable is not set"
            assert os.environ.get("DB_PASSWORD") is not None, \
                "DB_PASSWORD environment variable is not set"
            assert os.environ.get("SQL_ECHO", "false").lower() in ("true", "false"), \
                "SQL_ECHO environment variable must be 'true' or 'false'"

            assert os.environ.get("DEBUG", "false").lower() in ("true", "false"), \
                "DEBUG environment variable must be 'true' or 'false'"
            assert os.environ.get("ALLOW_ALL_ORIGINS", "false").lower() in ("true", "false"), \
                "ALLOW_ALL_ORIGINS environment variable must be 'true' or 'false'"
            assert os.environ.get("PROXY_EXTERNAL_IMAGES", "false").lower() in ("true", "false"), \
                "PROXY_EXTERNAL_IMAGES environment variable must be 'true' or 'false'"

            assert os.environ.get("CONTEXT", AppContext.CONSOLE.value) in AppContext.as_list(), \
                f"CONTEXT environment variable must be one of: {', '.join(AppContext.as_list())}"
            assert os.environ.get("BUILD_NUMBER") is None or os.environ.get("BUILD_NUMBER").isdigit(), \
                "BUILD_NUMBER environment variable must be a valid integer"

            data_dir = os.environ.get("DATA_DIR", "data")
            web_dir = os.environ.get("WEB_DIR", "web")

            with open(os.path.join(data_dir, "release_groups.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
                jsonschema.validate(data, RELEASE_GROUPS_JSON_SCHEMA)

                release_groups_map = {release_group.name: release_group for release_group
                                      in ReleaseGroup.many_from_dict(data["release_groups"])}

            if os.path.exists(custom_release_groups_file := os.path.join(data_dir, "release_groups_custom.json")):
                try:
                    with open(custom_release_groups_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        jsonschema.validate(data, RELEASE_GROUPS_JSON_SCHEMA)

                        custom_release_groups = ReleaseGroup.many_from_dict(data["release_groups"])
                        release_groups_map |= {
                            release_group.name: release_group for release_group in custom_release_groups
                        }
                except Exception as e:
                    logger.warning(f"Failed to load custom release groups: {e}")

            app_version, ui_minimum_version = None, None
            with open(".app-version", "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    key, value = line.strip().split("=")
                    if key == "app-ver":
                        app_version = value
                    elif key == "min-ui-ver":
                        ui_minimum_version = value
            assert app_version and ui_minimum_version, \
                "Invalid .app-version file: expected 'app-ver=x.y.z' and 'min-ui-ver=x.y.z'"

            if os.environ.get("ADMIN_PASSWORD_HASH") is not None:
                admin_password_hash = os.environ["ADMIN_PASSWORD_HASH"]
            else:
                from utils.helpers.crypto_helpers import hash_password
                admin_password_hash = hash_password(os.environ["ADMIN_PASSWORD"])
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            exit(1)

        return cls(
            port=int(os.environ["PORT"]),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            admin_username=os.environ["ADMIN_USERNAME"],
            admin_password_hash=admin_password_hash,
            jwt_secret=os.environ["JWT_SECRET"],
            db_host=os.environ["DB_HOST"],
            db_port=int(os.environ["DB_PORT"]),
            db_name=os.environ["DB_NAME"],
            db_user=os.environ["DB_USER"],
            db_password=os.environ["DB_PASSWORD"],
            sql_echo=os.environ.get("SQL_ECHO", "false").lower() == "true",
            debug=os.environ.get("DEBUG", "false").lower() == "true",
            allow_all_origins=os.environ.get("ALLOW_ALL_ORIGINS", "false").lower() == "true",
            proxy_external_images=os.environ.get("PROXY_EXTERNAL_IMAGES", "false").lower() == "true",
            app_version=AppVersion.from_string(app_version),
            ui_minimum_version=AppVersion.from_string(ui_minimum_version),
            context=AppContext(os.environ.get("CONTEXT", AppContext.CONSOLE.value)),
            build_number=int(os.environ["BUILD_NUMBER"]) if os.environ.get("BUILD_NUMBER") else None,
            data_dir=data_dir,
            web_dir=web_dir,
            release_groups_map=release_groups_map,
            user_settings=None,  # noqa: filled in on startup
        )


try:
    config = _Config.init()
except Exception as e_:
    logger.error(f"Failed to init config instance: {e_}")
    exit(1)
