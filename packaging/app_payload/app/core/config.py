from __future__ import annotations

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


# Project root, used to anchor the SQLite file regardless of CWD.
# app/core/config.py -> parents[0]=core, [1]=app, [2]=project root
_BASE_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_SQLITE_PATH = _BASE_DIR / "xingshi_v2.db"
_DEFAULT_SQLITE_URL = f"sqlite+aiosqlite:///{_DEFAULT_SQLITE_PATH.as_posix()}"


class AppConfig(BaseSettings):
    database_url: str = Field(
        default=_DEFAULT_SQLITE_URL,
        description="SQLAlchemy async database URL. Default: local SQLite (xingshi_v2.db).",
    )
    database_url_sync: str = Field(
        default="",
        description="Sync fallback for Alembic (auto-derived from database_url if empty).",
    )
    checkpoint_db_url: str = Field(
        default="",
        description="LangGraph checkpointer database URL (defaults to database_url if empty).",
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


# Single source of truth. .env can override via DATABASE_URL=...
DATABASE_URL: str = os.getenv("DATABASE_URL", "") or get_config().database_url


class KBSettings(BaseSettings):
    """KB platform plumbing: Qdrant, Redis, gray cutover. Distinct from AppConfig."""
    qdrant_master_host: str = "localhost"
    qdrant_replica_host: str = "localhost"
    qdrant_port: int = 6333
    redis_host: str = "localhost"
    redis_port: int = 6379
    health_check_interval_s: int = 10
    behavior_log_spool_dir: str = "./spool/agent_log"  # relative-to-cwd; override via KB_BEHAVIOR_LOG_SPOOL_DIR
    read_backend_percentage: int = 0  # 0..100, gray cutover for LangChain path
    dual_write_legacy: bool = True

    model_config = {
        "env_file": ".env",
        "env_prefix": "KB_",
        "extra": "ignore",
    }


kb_settings = KBSettings()
