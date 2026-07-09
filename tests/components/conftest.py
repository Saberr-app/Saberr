import pytest_asyncio


@pytest_asyncio.fixture
async def bound_session(mock_db):
    """Back-compat handle to the fake session bound by `mock_db`. Repos are mocked per-test, so this
    is just a marker / accessor; nothing is written to a real database."""
    yield mock_db
