from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.exceptions import ValidationException
from components.api_components import login_api_component
from components.api_components.login_api_component import LoginAPIComponent
from config import config
from constants import AppContext
from api.schemas.login_schemas import ResetPasswordRequest


@dataclass
class Case:
    id: str
    context: AppContext = AppContext.WINDOWS
    reset_code: str | None = None
    old_password: str | None = None
    stored_code: str | None = "1234"
    old_password_valid: bool = True
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="rejected outside the windows runtime",
         context=AppContext.CONSOLE, reset_code="1234", expected_exception=ValidationException),
    Case(id="neither reset code nor old password is rejected",
         reset_code=None, old_password=None, expected_exception=ValidationException),
    Case(id="both reset code and old password is rejected",
         reset_code="1234", old_password="old", expected_exception=ValidationException),
    Case(id="wrong reset code is rejected",
         reset_code="9999", stored_code="1234", expected_exception=ValidationException),
    Case(id="invalid old password is rejected",
         old_password="old", old_password_valid=False, expected_exception=ValidationException),
    # happy paths persist the new hash + fresh jwt secret
    Case(id="valid reset code resets the password",
         reset_code="1234", stored_code="1234"),
    Case(id="valid old password resets the password",
         old_password="old", old_password_valid=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_reset_password(case: Case, mocker):
    mocker.patch.object(config, "context", case.context)
    mocker.patch.object(config, "admin_password_hash", "stored-hash")
    mocker.patch.object(login_api_component, "PASSWORD_RESET_CODE_DETAILS",
                        {"code": case.stored_code, "file_path": "{data_dir}/reset_code"})
    mocker.patch.object(login_api_component, "verify_password", return_value=case.old_password_valid)
    mocker.patch.object(login_api_component, "hash_password", return_value="new-hash")
    mocker.patch.object(login_api_component, "thread_out", AsyncMock())
    mocker.patch.object(login_api_component.secrets, "token_hex", return_value="ab" * 32)
    # config.json read (async) then write (sync)
    read_handle = MagicMock()
    read_handle.read = AsyncMock(return_value='{"credentials": {}}')
    aiofiles_open = MagicMock()
    aiofiles_open.return_value.__aenter__ = AsyncMock(return_value=read_handle)
    aiofiles_open.return_value.__aexit__ = AsyncMock(return_value=False)
    mocker.patch.object(login_api_component.aiofiles, "open", aiofiles_open)
    mocker.patch("builtins.open", mocker.mock_open())
    mocker.patch.object(login_api_component.json, "dump")

    body = ResetPasswordRequest(reset_code=case.reset_code, old_password=case.old_password,
                                new_password="new-password")

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await LoginAPIComponent().reset_password(body)
        assert config.admin_password_hash == "stored-hash"  # unchanged on rejection
        return

    await LoginAPIComponent().reset_password(body)
    assert config.admin_password_hash == "new-hash"
    assert config.jwt_secret == ("ab" * 32).encode("utf-8")
