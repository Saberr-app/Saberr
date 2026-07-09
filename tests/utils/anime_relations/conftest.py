import asyncio

import pytest

from utils.anime_relations import AnimeRelations


@pytest.fixture
def make_relations():
    def _make(*, anilist_tvdb=None, tvdb_anilist=None, offset_map=None, episode_count=None):
        ar = AnimeRelations.__new__(AnimeRelations)  # bypass __init__ (avoids AssetComponent)
        ar._lock = asyncio.Lock()
        ar._ANILIST_TVDB_MAPPINGS = anilist_tvdb or {}
        ar._TVDB_ANILIST_MAPPINGS = tvdb_anilist or {}
        ar._ANIME_RELATIONS_OFFSET_MAP = offset_map or {}
        ar._ANIME_RELATIONS_OFFSET_EPISODE_COUNT_MAP = episode_count or {}
        return ar

    return _make


@pytest.fixture
def mock_overrides(mocker):
    """Patch the mapping-override repo lookup used by the public resolution methods."""
    def _patch(overrides):
        return mocker.patch(
            "repositories.mapping_override_repo.MappingOverrideRepo.get_mapping_overrides_for_anime",
            return_value=overrides)

    return _patch