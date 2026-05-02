import asyncio
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all model modules so Base.metadata is fully populated.
# This MUST be done before setting target_metadata, otherwise
# --autogenerate will produce an empty migration.
from app.models.base import Base
import app.models.user       # noqa: F401 — registers User, StudentProfile
import app.models.course      # noqa: F401 — registers Course, SceneOutline, Slide
import app.models.classroom   # noqa: F401 — registers ClassroomSession, QuizRecord, AgentTurnRecord

target_metadata = Base.metadata


def get_url():
    return config.get_main_option("sqlalchemy.url")


def _is_async_url(url: str) -> bool:
    return "+async" in url or url.startswith("mysql+aiomysql://") or url.startswith("postgresql+asyncpg://")


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    from sqlalchemy.ext.asyncio import async_engine_from_config

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def _run_sync_migrations() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


def run_migrations_online() -> None:
    url = get_url()
    if _is_async_url(url or ""):
        asyncio.run(_run_async_migrations())
    else:
        _run_sync_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
