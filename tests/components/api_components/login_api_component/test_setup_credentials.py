from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.exceptions import ValidationException
from components.api_components import login_api_component
from components.api_components.login_api_component import LoginAPIComponent
from config import config
from constants import AppContext
from api.schemas.login_schemas import CredentialsSetupRequest


@dataclass
class Case:
    id: str
    context: AppContext = AppContext.WINDOWS
    existing_username: str | None = None
    existing_hash: str | None = None
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="rejected outside the windows runtime",
         context=AppContext.CONSOLE, expected_exception=ValidationException),
    Case(id="rejected when credentials already set",
         existing_username="admin", existing_hash="hash", expected_exception=ValidationException),
    # happy path persists username + hash + fresh jwt secret
    Case(id="stores credentials when none are set"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_setup_credentials(case: Case, mocker):
    mocker.patch.object(config, "context", case.context)
    mocker.patch.object(config, "admin_username", case.existing_username)
    mocker.patch.object(config, "admin_password_hash", case.existing_hash)
    mocker.patch.object(login_api_component, "hash_password", return_value="new-hash")
    mocker.patch.object(login_api_component.secrets, "token_hex", return_value="cd" * 32)
    read_handle = MagicMock()
    read_handle.read = AsyncMock(return_value='{"credentials": {}}')
    aiofiles_open = MagicMock()
    aiofiles_open.return_value.__aenter__ = AsyncMock(return_value=read_handle)
    aiofiles_open.return_value.__aexit__ = AsyncMock(return_value=False)
    mocker.patch.object(login_api_component.aiofiles, "open", aiofiles_open)
    mocker.patch("builtins.open", mocker.mock_open())
    mocker.patch.object(login_api_component.json, "dump")

    body = CredentialsSetupRequest(username="alice", password="secret")

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await LoginAPIComponent().setup_credentials(body)
        assert config.admin_username == case.existing_username  # unchanged on rejection
        return

    await LoginAPIComponent().setup_credentials(body)
    assert config.admin_username == "alice"
    assert config.admin_password_hash == "new-hash"
    assert config.jwt_secret == ("cd" * 32).encode("utf-8")
