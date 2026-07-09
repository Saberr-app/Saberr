from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.exceptions import ValidationException
from components.api_components import login_api_component
from components.api_components.login_api_component import LoginAPIComponent
from config import config
from constants import AppContext


@dataclass
class Case:
    id: str
    context: AppContext
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="rejected outside the windows runtime",
         context=AppContext.CONSOLE, expected_exception=ValidationException),
    # happy path stores a fresh zero-padded 8-digit code
    Case(id="generates and stores an 8-digit reset code", context=AppContext.WINDOWS),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_request_password_reset(case: Case, mocker):
    mocker.patch.object(config, "context", case.context)
    reset_details = {"code": None, "file_path": "{data_dir}/reset_code"}
    mocker.patch.object(login_api_component, "PASSWORD_RESET_CODE_DETAILS", reset_details)
    # randbelow -> a value that must be zero-padded to 8 digits
    mocker.patch.object(login_api_component.secrets, "randbelow", return_value=42)
    write_handle = MagicMock()
    write_handle.write = AsyncMock()
    aiofiles_open = MagicMock()
    aiofiles_open.return_value.__aenter__ = AsyncMock(return_value=write_handle)
    aiofiles_open.return_value.__aexit__ = AsyncMock(return_value=False)
    mocker.patch.object(login_api_component.aiofiles, "open", aiofiles_open)

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await LoginAPIComponent().request_password_reset()
        assert reset_details["code"] is None  # unchanged on rejection
        return

    await LoginAPIComponent().request_password_reset()
    assert reset_details["code"] == "00000042"
    write_handle.write.assert_awaited_once_with("00000042")
