import pytest

from config import config


@pytest.fixture(scope="session")
def release_groups_map():
    return config.release_groups_map
