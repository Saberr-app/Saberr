from dataclasses import dataclass, field
from unittest.mock import AsyncMock

import pytest

from api.schemas.torrent_schemas import TorrentSearchRequest
from common.exceptions import ValidationException
from components.api_components.torrent_api_component import TorrentAPIComponent
from components.service_components.rss_component import RSSComponent
from config import config

_RSS_GET = "components.service_components.rss_component.RSSComponent.get_torrents"
_GET_TORRENTS = "components.api_components.torrent_api_component.TorrentAPIComponent.get_torrents"

_RELEASE_GROUPS = {"GroupA": None, "GroupB": None}


def _component() -> TorrentAPIComponent:
    component = TorrentAPIComponent.__new__(TorrentAPIComponent)
    component._rss_component = RSSComponent.__new__(RSSComponent)
    return component


@dataclass
class Case:
    id: str
    request_kwargs: dict = field(default_factory=dict)
    expected_release_groups: list[str] | None = None
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="no release groups falls back to all configured",
         request_kwargs=dict(query="naruto"), expected_release_groups=["GroupA", "GroupB"]),
    Case(id="valid subset is forwarded as-is",
         request_kwargs=dict(release_groups=["GroupA"]), expected_release_groups=["GroupA"]),
    Case(id="unknown release group rejected",
         request_kwargs=dict(release_groups=["GroupX"]), expected_exception=ValidationException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_search_torrents(case: Case, mocker):
    mocker.patch.object(config, "release_groups_map", _RELEASE_GROUPS)
    rss_get = mocker.patch(_RSS_GET, new_callable=AsyncMock, return_value=[])
    sentinel = object()
    get_torrents = mocker.patch(_GET_TORRENTS, new_callable=AsyncMock, return_value=sentinel)
    body = TorrentSearchRequest(**case.request_kwargs)

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await _component().search_torrents(body)
        rss_get.assert_not_called()
        return

    result = await _component().search_torrents(body)

    assert result is sentinel
    assert rss_get.await_args.kwargs["release_groups"] == case.expected_release_groups
    get_torrents.assert_awaited_once()
