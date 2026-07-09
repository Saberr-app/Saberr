import base64
import datetime
import hmac
import json
import os.path
import secrets
from pathlib import Path

import aiofiles
import jwt

from app_state import PASSWORD_RESET_CODE_DETAILS
from common.context_helpers import thread_out, get_request_metadata
from common.db import get_session
from common.decorators import api_component
from common.exceptions import UnauthorizedException, ValidationException
from components import BaseComponent
from config import config
from constants import NotificationCode, NotificationLevel, JWT_ALGORITHM, AppContext
from api.schemas.login_schemas import LoginRequest, LoginResponse, CredentialsStatusResponse, CredentialsSetupRequest, \
    ResetPasswordRequest
from components.audit_log_component import AuditLogComponent
from components.notification_component import NotificationComponent
from utils.helpers.crypto_helpers import verify_password, hash_password

_STAY_LOGGED_IN_DURATION = datetime.timedelta(weeks=4)
_DEFAULT_DURATION = datetime.timedelta(days=1)


class LoginAPIComponent(BaseComponent):

    def __init__(self):
        super().__init__()
        self._audit_log_component = AuditLogComponent()
        self._notification_component = NotificationComponent()

    @api_component
    async def authenticate(self, body: LoginRequest) -> LoginResponse:
        request_metadata = get_request_metadata()
        ip_address = request_metadata.ip_address
        browser = request_metadata.browser
        country = request_metadata.country

        username_ok = hmac.compare_digest(body.username, config.admin_username)
        password_ok = verify_password(config.admin_password_hash, body.password)
        if not (username_ok and password_ok):
            await self._audit_login(False, ip_address=ip_address, username=body.username,
                                    browser=browser, country=country)
            await get_session().commit()
            raise UnauthorizedException(detail="Invalid username or password")

        expires_in = _STAY_LOGGED_IN_DURATION if body.stay_logged_in else _DEFAULT_DURATION
        now = datetime.datetime.now(datetime.UTC)
        expires_at = now + expires_in
        token = jwt.encode(
            {"sub": config.admin_username, "iat": now, "exp": expires_at},
            config.jwt_secret,
            algorithm=JWT_ALGORITHM,
        )
        await self._audit_login(True, ip_address=ip_address, browser=browser, country=country)
        await self._notification_component.send_notification(
            code=NotificationCode.LOGIN,
            level=NotificationLevel.INFO,
            text="User logged in",
            identifier={"ip_address": ip_address, "country": country, "browser": browser},
        )
        return LoginResponse(token=token, expires_at=int(expires_at.timestamp()))

    async def _audit_login(self, succeeded: bool, ip_address: str | None, browser: str | None,
                           country: str | None, username: str | None = None):
        await self._audit_log_component.log_login_succeeded(
            ip_address=ip_address, browser=browser, country=country
        ) if succeeded else await self._audit_log_component.log_login_failed(
            ip_address=ip_address, browser=browser, country=country, username=username
        )

    @api_component
    async def get_credentials_status(self) -> CredentialsStatusResponse:
        return CredentialsStatusResponse(
            is_set=(bool(config.admin_username) and bool(config.admin_password_hash))
            or config.context == AppContext.CONSOLE,
            context=config.context
        )

    @api_component
    async def setup_credentials(self, body: CredentialsSetupRequest):
        if config.context != AppContext.WINDOWS:
            raise ValidationException("API not available for this runtime environment.")
        if config.admin_username and config.admin_password_hash:
            raise ValidationException("Credentials already set")
        config_file_path = os.path.join(config.data_dir, 'config', 'config.json')
        async with aiofiles.open(config_file_path, 'r') as config_file:
            config_data = json.loads(await config_file.read())
        password_hash = hash_password(body.password)
        jwt_token = secrets.token_hex(32).encode("utf-8")
        config_data["credentials"] |= {
            "username": body.username,
            "password": password_hash,
            "jwt_secret": base64.b64encode(jwt_token).decode("ascii")
        }
        with open(config_file_path, 'w') as config_file:
            json.dump(config_data, config_file, indent=4)
        config.admin_username = body.username
        config.admin_password_hash = password_hash
        config.jwt_secret = jwt_token

    @api_component
    async def request_password_reset(self):
        if config.context != AppContext.WINDOWS:
            raise ValidationException("API not available for this runtime environment.")
        password_reset_code_file_path = PASSWORD_RESET_CODE_DETAILS['file_path'].format(data_dir=config.data_dir)
        PASSWORD_RESET_CODE_DETAILS['code'] = f"{secrets.randbelow(100_000_000):08d}"
        async with aiofiles.open(password_reset_code_file_path, 'w') as code_file:
            await code_file.write(PASSWORD_RESET_CODE_DETAILS['code'])

    @api_component
    async def reset_password(self, body: ResetPasswordRequest):
        if config.context != AppContext.WINDOWS:
            raise ValidationException("API not available for this runtime environment.")
        if not body.reset_code and not body.old_password:
            raise ValidationException("Reset code or old password is required")
        if body.reset_code and body.old_password:
            raise ValidationException("Only one of reset code or old password is required")
        if body.reset_code:
            if body.reset_code != PASSWORD_RESET_CODE_DETAILS['code']:
                raise ValidationException("Invalid reset code")
        elif not verify_password(config.admin_password_hash, body.old_password):
            raise ValidationException("Invalid old password")

        password_reset_code_file_path = PASSWORD_RESET_CODE_DETAILS['file_path'].format(data_dir=config.data_dir)
        try:
            await thread_out(Path(password_reset_code_file_path).unlink, missing_ok=True)
        except:
            pass
        PASSWORD_RESET_CODE_DETAILS['code'] = None

        config_file_path = os.path.join(config.data_dir, 'config', 'config.json')
        async with aiofiles.open(config_file_path, 'r') as config_file:
            config_data = json.loads(await config_file.read())
        password_hash = hash_password(body.new_password)
        jwt_token = secrets.token_hex(32).encode("utf-8")
        config_data["credentials"] |= {
            "password": password_hash,
            "jwt_secret": base64.b64encode(jwt_token).decode("ascii")
        }
        with open(config_file_path, 'w') as config_file:
            json.dump(config_data, config_file, indent=4)
        config.admin_password_hash = password_hash
        config.jwt_secret = jwt_token
