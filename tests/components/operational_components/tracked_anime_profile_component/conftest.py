from types import SimpleNamespace

import pytest

from constants import Encoding, Resolution, VideoSource, ReleaseCriteriaProperty


@pytest.fixture
def make_profile():
    """Build an in-memory stand-in for a TrackedAnimeProfile ORM row.

    `update_tracked_anime_profile` only reads attributes off the profile (and `.value` for the enum
    list fields), so a SimpleNamespace with matching attributes is enough — no DB or ORM needed.
    """
    def _make(*, preferred_release_groups=None, preferred_encodings=None, preferred_resolutions=None,
              preferred_language_codes=None, preferred_sources=None, language_codes_restricted=False,
              sources_restricted=False, accept_release_upgrades=True, priorities_sorted=None,
              tracked_anime_list=None):
        return SimpleNamespace(
            preferred_release_groups=preferred_release_groups if preferred_release_groups is not None else ["GroupA"],
            preferred_encodings=preferred_encodings if preferred_encodings is not None else [Encoding.HEVC],
            preferred_resolutions=preferred_resolutions if preferred_resolutions is not None else [Resolution.P1080],
            preferred_language_codes=preferred_language_codes if preferred_language_codes is not None else ["eng"],
            preferred_sources=preferred_sources if preferred_sources is not None else [VideoSource.CRUNCHYROLL],
            language_codes_restricted=language_codes_restricted,
            sources_restricted=sources_restricted,
            accept_release_upgrades=accept_release_upgrades,
            priorities_sorted=priorities_sorted if priorities_sorted is not None else [ReleaseCriteriaProperty.RESOLUTION],
            tracked_anime_list=tracked_anime_list if tracked_anime_list is not None else [],
        )
    return _make
