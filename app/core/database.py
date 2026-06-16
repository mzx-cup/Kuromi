from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import DATABASE_URL
from app.models.base import Base

logger = logging.getLogger("starlearn.db")

_engine: "create_async_engine | None" = None
_async_sessionmaker: "async_sessionmaker[AsyncSession] | None" = None


def get_engine():
    global _engine
    if _engine is None:
        connect_args = {}
        if DATABASE_URL.startswith("sqlite"):
            connect_args = {"timeout": 5}
        _engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_size=10,
            max_overflow=20,
            connect_args=connect_args,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _async_sessionmaker
    if _async_sessionmaker is None:
        _async_sessionmaker = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _async_sessionmaker


async def init_db(timeout_seconds: float = 10.0) -> bool:
    """Create all tables registered on Base.metadata. Idempotent.

    Safe to call on every startup; failures are logged and swallowed
    so a misconfigured DB never blocks app startup.
    """
    # Import model modules so their tables register on Base.metadata.
    from app.models import course  # noqa: F401

    async def _do_init():
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    try:
        await asyncio.wait_for(_do_init(), timeout=timeout_seconds)
        logger.info("[init_db] schema created (or already existed): %s", DATABASE_URL)
        return True
    except Exception as e:
        logger.exception("[init_db] schema creation failed: %s", e)
        return False


async def get_db():
    async with get_sessionmaker()() as session:
        try:
            yield session
        finally:
            await session.close()
