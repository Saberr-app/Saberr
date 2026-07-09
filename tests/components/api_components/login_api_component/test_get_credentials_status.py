from dataclasses import dataclass

import pytest

from components.api_components.login_api_component import LoginAPIComponent
from config import config
from constants import AppContext


@dataclass
class Case:
    id: str
    admin_username: str | None
    admin_password_hash: str | None
    context: AppContext
    expected_is_set: bool


CASES = [
    Case(id="both credentials set -> is_set",
         admin_username="admin", admin_password_hash="hash", context=AppContext.WINDOWS,
         expected_is_set=True),
    # console context is always considered set regardless of stored credentials
    Case(id="console context is always set",
         admin_username=None, admin_password_hash=None, context=AppContext.CONSOLE,
         expected_is_set=True),
    Case(id="missing credentials on windows -> not set",
         admin_username=None, admin_password_hash=None, context=AppContext.WINDOWS,
         expected_is_set=False),
    # only one half present is not enough
    Case(id="username without password hash is not set",
         admin_username="admin", admin_password_hash=None, context=AppContext.WINDOWS,
         expected_is_set=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_credentials_status(case: Case, mocker):
    mocker.patch.object(config, "admin_username", case.admin_username)
    mocker.patch.object(config, "admin_password_hash", case.admin_password_hash)
    mocker.patch.object(config, "context", case.context)

    result = await LoginAPIComponent().get_credentials_status()

    assert result.is_set is case.expected_is_set
    assert result.context == case.context
