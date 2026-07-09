from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from config import config
from constants import Encoding, Resolution, VideoSource, ReleaseCriteriaProperty

_PROFILE_COMPONENT = ("components.operational_components.tracked_anime_profile_component"
                      ".TrackedAnimeProfileComponent")


def _default_profile():
    return SimpleNamespace(
        id=1, preferred_release_groups=["SubsPlease"], preferred_encodings=[Encoding.HEVC],
        preferred_resolutions=[Resolution.P1080], preferred_language_codes=["JP"],
        preferred_sources=[VideoSource.CRUNCHYROLL], language_codes_restricted=False,
        sources_restricted=False, accept_release_upgrades=True,
        priorities_sorted=[ReleaseCriteriaProperty.RESOLUTION])


@dataclass
class Case:
    id: str


CASES = [Case(id="maps config and profile into sections")]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_settings(case: Case, settings_api, mocker):
    profile = _default_profile()
    mocker.patch(f"{_PROFILE_COMPONENT}.get_default_tracked_anime_profile", return_value=profile)

    result = await settings_api.get_settings()
    us = config.user_settings

    assert result.general.timezone == us.timezone
    assert result.general.set_download_as_failed_after_minutes == us.set_download_as_failed_after_minutes
    assert result.general.anilist_preferred_title_language == us.anilist_preferred_title_language

    assert result.anilist.anilist_username == us.anilist_username
    assert result.anilist.anilist_user_token == ("SET" if us.anilist_user_token is not None else "UNSET")
    assert result.anilist.anilist_user_data is None

    assert result.qbit.qbit_base_url == us.qbit_base_url
    assert result.qbit.organize_downloads == us.organize_downloads
    assert result.qbit.apply_anime_title_as_torrent_tag == us.apply_anime_title_as_torrent_tag

    assert result.rss.rss_check_frequency == us.rss_check_frequency
    assert result.rss.auto_download == us.auto_download
    assert result.rss.rss_category == us.rss_category
    assert result.processing.tvdb_structure_enabled_default == us.tvdb_structure_enabled_default
    assert result.discord.discord_user_id == us.discord_user_id

    # profile section mapped from the default profile
    assert result.profile.preferred_release_groups == profile.preferred_release_groups
    assert result.profile.priorities_sorted == profile.priorities_sorted

    # meta carries the formatting-token maps and available release groups
    assert result.meta.show_directory_formatting_tokens
    # sourced from config.release_group_names, an unordered set
    assert set(result.meta.available_release_groups) == set(config.release_groups_map.keys())
