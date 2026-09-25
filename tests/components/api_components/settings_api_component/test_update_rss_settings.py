from dataclasses import dataclass

import pytest

from config import config
from api.schemas.settings_schemas import RSSSettings
from constants import RSSCategory, ProxyProtocol


@dataclass
class Case:
    id: str
    body: RSSSettings
    expected_proxy_host: str | None = None
    expected_proxy_protocol: ProxyProtocol | None = None


CASES = [
    Case(id="persists and returns rss section",
         body=RSSSettings(auto_download=False, rss_check_frequency=900,
                          rss_category=RSSCategory.ENGLISH_TRANSLATED,
                          rss_proxy_config=None, rss_proxy_torrent_files_enabled=True)),
    Case(id="persists http proxy as dto and echoes it back as a string",
         body=RSSSettings(auto_download=False, rss_check_frequency=900,
                          rss_category=RSSCategory.ENGLISH_TRANSLATED,
                          rss_proxy_config="http://u:p@1.2.3.4:3128",
                          rss_proxy_torrent_files_enabled=True),
         expected_proxy_host="1.2.3.4", expected_proxy_protocol=ProxyProtocol.HTTP),
    Case(id="persists socks5 proxy with torrent file proxying disabled",
         body=RSSSettings(auto_download=False, rss_check_frequency=900,
                          rss_category=RSSCategory.ENGLISH_TRANSLATED,
                          rss_proxy_config="socks5://1.2.3.4:1080",
                          rss_proxy_torrent_files_enabled=False),
         expected_proxy_host="1.2.3.4", expected_proxy_protocol=ProxyProtocol.SOCKS5),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_rss_settings(case: Case, bound_session, settings_api):
    result = await settings_api.update_rss_settings(case.body)
    assert config.user_settings.auto_download is False
    assert config.user_settings.rss_check_frequency == 900
    assert config.user_settings.rss_category == RSSCategory.ENGLISH_TRANSLATED
    assert config.user_settings.rss_proxy_torrent_files_enabled is case.body.rss_proxy_torrent_files_enabled
    assert result.auto_download is False
    assert result.rss_check_frequency == 900
    assert result.rss_category == RSSCategory.ENGLISH_TRANSLATED
    assert result.rss_proxy_torrent_files_enabled is case.body.rss_proxy_torrent_files_enabled

    if case.expected_proxy_host is None:
        assert config.user_settings.rss_proxy_config is None
        assert result.rss_proxy_config is None
        return
    assert config.user_settings.rss_proxy_config.host == case.expected_proxy_host
    assert config.user_settings.rss_proxy_config.protocol is case.expected_proxy_protocol
    assert result.rss_proxy_config == case.body.rss_proxy_config
