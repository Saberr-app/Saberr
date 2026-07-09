from dataclasses import dataclass

import pytest

from components.api_components.system_api_component import SystemAPIComponent


@dataclass
class Case:
    id: str


CASES = [
    Case(id="requests a server shutdown"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_shutdown(case: Case, mocker):
    request_shutdown = mocker.patch("system.server.request_shutdown")

    await SystemAPIComponent().shutdown()

    request_shutdown.assert_called_once_with()
