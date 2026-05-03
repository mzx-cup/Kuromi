from __future__ import annotations

import os
from pydantic import Field
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    database_url: str = Field(
        default="mysql+asyncmy://root:@localhost:3306/starlearn",
        description="SQLAlchemy async database URL (asyncmy driver)",
    )
    database_url_sync: str = Field(
        default="",
        description="Sync fallback for Alembic (auto-derived from database_url if empty)",
    )
    checkpoint_db_url: str = Field(
        default="",
        description="LangGraph checkpointer database URL (defaults to database_url if empty)",
    )
    app_debug: bool = Field(default=False, validation_alias="APP_DEBUG")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./starlearn_v2.db",
)
