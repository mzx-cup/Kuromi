"""3-layer ResilientBehaviorLogger (DB -> Redis -> Disk).

Layered write strategy: a log entry is always written to the first layer
that accepts it. Order of preference:

    1. PostgreSQL (``db_insert``) — the canonical store.
    2. Redis buffer (``redis_push``) — fast retry buffer if DB is unhealthy.
    3. Disk spool (``disk_append``) — durable last-resort buffer.

If all three layers fail, the entry is rejected and the caller receives
a ``LogResult(status="rejected")`` so it can decide how to react (raise,
retry later, drop, etc).

Each layer is a module-level callable so tests can patch
``app.services.agent_log.resilient_logger.<name>`` directly.

NOTE: ``db_insert`` writes via a dedicated sync engine created at module
import time. On any failure (engine missing, malformed URL, connection
drop, constraint violation) it returns False so the resilient logger can
fall through to the Redis buffer and disk spool layers.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.models.agent_behavior_log import AgentBehaviorLog
from app.services.agent_log.buffer import redis_push
from app.services.agent_log.disk_spool import disk_append


def _to_sync_url(url: str) -> str:
    """Convert an async SQLAlchemy URL to its sync equivalent.

    Mirrors the mapping table in ``app/repositories/orm/knowledge_node.py``
    so the default sqlite+aiosqlite URL becomes a usable sync sqlite URL.
    """
    if not url:
        return ""
    mapping = {
        "postgresql+asyncpg://": "postgresql+psycopg2://",
        "sqlite+aiosqlite://": "sqlite://",
        "mysql+aiomysql://": "mysql+pymysql://",
    }
    for async_prefix, sync_prefix in mapping.items():
        if url.startswith(async_prefix):
            return sync_prefix + url[len(async_prefix):]
    # Fallback: strip any "+driver" suffix so a sync driver is selected.
    if "+" in url.split("://", 1)[0]:
        scheme = url.split("://", 1)[0].split("+", 1)[0]
        rest = url.split("://", 1)[1]
        return f"{scheme}://{rest}"
    return url


def _build_engine() -> "Engine | None":
    url = os.getenv("DATABASE_URL", "")
    sync_url = _to_sync_url(url)
    if not sync_url:
        return None
    try:
        return create_engine(
            sync_url,
            future=True,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
    except Exception:
        # Malformed URL or driver missing — let db_insert no-op.
        return None


_engine = _build_engine()
_SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False) if _engine else None


def db_insert(log: AgentBehaviorLog) -> bool:
    """Insert ``log`` into the canonical store (PostgreSQL).

    Wired in S3.2: real ORM insert using a dedicated sync engine.
    Returns True on success, False on any failure (caller falls through
    to Redis/disk layers).
    """
    if _SessionLocal is None:
        return False
    try:
        with _SessionLocal() as session:
            session.add(log)
            session.commit()
        return True
    except Exception:  # noqa: BLE001 - fail-open contract.
        return False


@dataclass
class LogResult:
    """Outcome of a ``ResilientBehaviorLogger.log`` call."""
    status: str  # one of: "ok", "deferred", "deferred_disk", "rejected"
    layer: str = ""  # which layer accepted the write: "db" / "redis" / "disk" / ""
    error: str = ""


class ResilientBehaviorLogger:
    """3-layer fail-open logger. Always tries DB first; on failure falls
    through to Redis, then to disk. Never raises on layer failures — the
    caller decides what to do with a rejected entry.
    """

    def log(self, log: AgentBehaviorLog) -> LogResult:
        # Layer 1: DB.
        try:
            if db_insert(log):
                return LogResult(status="ok", layer="db")
        except Exception as exc:  # noqa: BLE001 - fail-open contract.
            # If db_insert raises, treat as DB-failed so we fall through
            # to Redis/disk. The S0.3 stub returns False directly, so this
            # branch only fires once S3.2 wires the real DB layer and a
            # transient error escapes (e.g. connection drop).
            db_error = str(exc)
        else:
            db_error = ""

        # Layer 2: Redis buffer.
        try:
            if redis_push(_payload(log)):
                return LogResult(status="deferred", layer="redis", error=db_error)
        except Exception as exc:  # noqa: BLE001
            redis_error = str(exc)
        else:
            redis_error = ""

        # Layer 3: Disk spool (last resort, durable).
        try:
            if disk_append(_payload(log)):
                return LogResult(
                    status="deferred_disk",
                    layer="disk",
                    error=db_error or redis_error,
                )
        except Exception as exc:  # noqa: BLE001
            disk_error = str(exc)
        else:
            disk_error = ""

        return LogResult(status="rejected", error=db_error or redis_error or disk_error)


def _payload(log: AgentBehaviorLog) -> dict[str, Any]:
    """Serialize an AgentBehaviorLog to a plain dict for Redis/disk layers."""
    return {
        "agent_id": log.agent_id,
        "user_id": log.user_id,
        "action_type": log.action_type,
        "input_summary": log.input_summary,
        "output_text": log.output_text,
        "citations": log.citations,
    }