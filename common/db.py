# noinspection PyPackageRequirements
import contextvars
import inspect
from typing import Callable, Coroutine

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from contextlib import asynccontextmanager


from config import config

engine = create_async_engine(
    f"mysql+aiomysql://{config.db_user}:{config.db_password}@"
    f"{config.db_host}:{config.db_port}/"
    f"{config.db_name}",
    echo=config.sql_echo,
    pool_size=15,
    max_overflow=30,
    connect_args={
        "init_command": "SET time_zone = '+00:00'",
    },
    isolation_level="READ COMMITTED",
)

AsyncSessionLocal: async_sessionmaker = async_sessionmaker(bind=engine, expire_on_commit=False)
# Per context: (session, post_commit_actions, post_rollback_actions)
_session_ctx: contextvars.ContextVar[tuple[AsyncSession, list[tuple], list[tuple]]] = \
    contextvars.ContextVar("session")


@asynccontextmanager
async def session_context():
    async with AsyncSessionLocal() as session:
        token = _session_ctx.set((session, [], []))
        try:
            yield session
        finally:
            _session_ctx.reset(token)
            await session.close()


def get_session() -> AsyncSession:
    return _session_ctx.get()[0]


def add_post_commit_action(action: Callable | Coroutine, *args, **kwargs):
    """
    Adds an action to be executed after the current transaction is committed.
    Args:
        action: A callable that will be executed after commit.
    """
    session, post_commit_actions, post_rollback_actions = _session_ctx.get()
    post_commit_actions.append((action, args, kwargs))
    _session_ctx.set((session, post_commit_actions, post_rollback_actions))


async def execute_post_commit_actions():
    """
    Executes all actions that were added to the session context after the transaction is committed.
    """
    session, post_commit_actions, post_rollback_actions = _session_ctx.get()
    for action, args, kwargs in post_commit_actions:
        if not inspect.iscoroutinefunction(action):
            action(*args, **kwargs)
        else:
            await action(*args, **kwargs)
    _session_ctx.set((session, [], post_rollback_actions))


def add_post_rollback_action(action: Callable | Coroutine, *args, **kwargs):
    """
    Adds an action to be executed after the current transaction is rolled back.
    Args:
        action: A callable that will be executed after rollback.
    Returns:

    """
    session, post_commit_actions, post_rollback_actions = _session_ctx.get()
    post_rollback_actions.append((action, args, kwargs))
    _session_ctx.set((session, post_commit_actions, post_rollback_actions))


async def execute_post_rollback_actions():
    """
    Executes all actions that were added to the session context after the transaction is rolled back.
    """
    session, post_commit_actions, post_rollback_actions = _session_ctx.get()
    for action, args, kwargs in post_rollback_actions:
        if not inspect.iscoroutinefunction(action):
            action(*args, **kwargs)
        else:
            await action(*args, **kwargs)
    _session_ctx.set((session, [], []))
