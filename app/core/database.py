from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import DATABASE_URL
from app.models.base import Base

_engine: "create_async_engine | None" = None
_async_sessionmaker: "async_sessionmaker[AsyncSession] | None" = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _async_sessionmaker
    if _async_sessionmaker is None:
        _async_sessionmaker = async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _async_sessionmaker


async def get_db():
    async with get_sessionmaker()() as session:
        try:
            yield session
        finally:
            await session.close()
