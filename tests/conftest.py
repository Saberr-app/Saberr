"""Shared test fixtures.

Unit tests never touch a real database. `config` and `common.db`'s async engine are still built at
import time (importing almost anything drags in the app), so we set dummy env vars *before* importing
the app — but the engine object is only constructed, never connected.

The `mock_db` fixture (autouse) makes the whole session machinery inert: `get_session()`,
`session_context()` and `require_db_session` all resolve to a fake `AsyncMock` session that never
connects. Repository calls are mocked per-test (see `tests/support/mocks.py::patch_async_returns`),
so no SQL is ever emitted.

Pure-logic tests (formatters, recognition utils, etc.) need none of this — build objects in memory
and pass them in directly.
"""
import contextlib
import os
from unittest.mock import AsyncMock, MagicMock

# config._Config.init() validates these at import time. Tests use dummy values; setdefault lets a
# real env / CI override.
os.environ.setdefault("PORT", "8080")
os.environ.setdefault("ADMIN_USERNAME", "test")
os.environ.setdefault("ADMIN_PASSWORD", "test")
os.environ.setdefault("JWT_SECRET", "26cbe57a5baece110a2f4d2ae4cdc78da0a01353607205e6098f38aaf21e8238")
# DB engine is built at import time but never connects (repos are mocked); dummy values suffice.
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_NAME", "saber_test")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data.default"))


import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

# Prime `app_state` before anything imports `services`. `services/__init__` does
# `from app_state import CACHED_RESPONSES`, and `app_state` builds `AnimeRelations()` which pulls in
# `services.static_files_service` -> `from services import ThirdPartyService`. Importing `services`
# first hits that mid-initialization (ThirdPartyService undefined yet); importing `app_state` first
# (CACHED_RESPONSES is defined before the AnimeRelations() construction) resolves the order.
import app_state  # noqa: E402,F401

import common.db as db  # noqa: E402


@pytest.fixture(autouse=True)
def user_settings():
    """Populate `config.user_settings` with seed defaults (normally loaded from the DB at startup).
    Override per test with `config.config.user_settings = make_user_settings(...)`."""
    from config import config
    from tests.support.builders import make_user_settings
    config.user_settings = make_user_settings()
    yield config.user_settings


@pytest.fixture(autouse=True)
def default_mapping_overrides(mocker):
    """anime_relations resolution consults MappingOverrideRepo on every lookup. Default it to "no
    overrides" so flows that don't care about overrides don't reach the (mocked) DB. Tests exercising
    overrides re-patch this method with their own rows."""
    return mocker.patch(
        "repositories.mapping_override_repo.MappingOverrideRepo.get_mapping_overrides_for_anime",
        return_value=[])


@pytest_asyncio.fixture(autouse=True)
async def mock_db(monkeypatch):
    """Neutralize all session machinery so no test ever connects to a database.

    - `AsyncSessionLocal()` (used by `session_context` / `require_db_session`) yields a fake session.
    - `get_session()` returns that same fake session, so `Repo(get_session())` constructors work.
    Repository methods themselves are mocked per-test, so the fake session is never actually used.
    """
    fake_session = AsyncMock()
    # `add`/`expunge` etc. are sync in SQLAlchemy; keep them sync so stray repo calls against the fake
    # session don't leave unawaited coroutines.
    fake_session.add = MagicMock()
    fake_session.add_all = MagicMock()
    fake_session.expunge = MagicMock()
    fake_session.expunge_all = MagicMock()

    @contextlib.asynccontextmanager
    async def _fake_session_local():
        yield fake_session

    monkeypatch.setattr(db, "AsyncSessionLocal", _fake_session_local)
    token = db._session_ctx.set((fake_session, [], []))
    try:
        yield fake_session
    finally:
        db._session_ctx.reset(token)
