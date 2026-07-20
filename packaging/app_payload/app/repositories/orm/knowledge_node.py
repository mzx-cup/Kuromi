"""KnowledgeNode ORM Repository — L1 content layer (slice-s1).

This is the L1 (content layer) repository for the unified KB platform.
It is intentionally distinct from ``app.repositories.orm.knowledge``
which backs the M6 SM2 spaced-repetition flow on a different
``KnowledgeNode`` model (``app.models.knowledge.KnowledgeNode``).

Both files expose classes with similar names but serve different
schemas; callers must import from the correct module for the layer
they want.

File-name note: the implementation plan refers to
``app/repositories/orm/knowledge.py``, but that file already exists and
backs the SM2 repo. Per the plan-vs-reality corrections for S1.4, the
L1 repo lives here under the singular ``knowledge_node`` name.
"""
from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DATABASE_URL
from app.models.knowledge_node import KnowledgeNode  # noqa: F401  (register table on Base.metadata)


# ── Sync URL derivation ──────────────────────────────────────────────────
# The L1 ingestion path is a one-shot write — async is unnecessary.
# We derive a sync URL from the async ``DATABASE_URL`` (which defaults
# to ``sqlite+aiosqlite:///...``) by stripping the async driver suffix.
#
# Driver mapping rationale:
#   sqlite+aiosqlite  -> sqlite            (stdlib, no extra deps)
#   postgresql+asyncpg -> postgresql+psycopg2
#   mysql+aiomysql     -> mysql+pymysql
#   any other async-?  -> strip ``+<driver>`` and fall back to the bare
#                         scheme so SQLAlchemy picks its default driver.
#
# Tests can override the sync URL via the ``KB_L1_SYNC_DB_URL`` env var
# (e.g. a tmp SQLite path) and call ``reset_session_factory()`` to
# rebuild the engine without reimporting the module.

def _to_sync_url(url: str) -> str:
    if not url:
        return "sqlite://"
    replacements = (
        ("sqlite+aiosqlite", "sqlite"),
        ("postgresql+asyncpg", "postgresql+psycopg2"),
        ("mysql+aiomysql", "mysql+pymysql"),
    )
    for async_drv, sync_drv in replacements:
        if url.startswith(async_drv + "://"):
            return sync_drv + url[len(async_drv):]
    if "+" in url.split("://", 1)[0]:
        scheme, rest = url.split("://", 1)
        bare = scheme.split("+", 1)[0]
        return f"{bare}://{rest}"
    return url


def _resolve_sync_url() -> str:
    """Tests can pin a fresh tmp SQLite path via KB_L1_SYNC_DB_URL."""
    override = os.environ.get("KB_L1_SYNC_DB_URL")
    if override:
        return override
    return _to_sync_url(DATABASE_URL)


_engine: Engine = create_engine(_resolve_sync_url(), future=True)
SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False, class_=Session)


def reset_session_factory(db_url: Optional[str] = None) -> None:
    """Rebuild the module-level sync engine + sessionmaker.

    Used by tests that point the L1 repo at an isolated SQLite file.
    Pass ``db_url`` explicitly to override, or set the
    ``KB_L1_SYNC_DB_URL`` env var first.
    """
    global _engine, SessionFactory
    if db_url is not None:
        url = db_url
    else:
        url = _resolve_sync_url()
    _engine = create_engine(url, future=True)
    SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False, class_=Session)


# ── Sync ORM implementation ──────────────────────────────────────────────

class OrmKnowledgeRepository:
    """Sync SQLAlchemy repository for L1 ``KnowledgeNode``.

    No-arg constructor — uses the module-level ``SessionFactory`` so the
    L1 ingestion path can call ``OrmKnowledgeRepository().insert(node)``
    without threading a session through every call site (mirrors the
    SM2 repo's ``def __init__(self, session: Session = None)`` pattern).
    """
    def __init__(self) -> None:
        self._sf = SessionFactory

    def insert(self, node: KnowledgeNode) -> None:
        with self._sf() as s:
            s.add(node)
            s.commit()

    def get(self, node_id: str) -> KnowledgeNode | None:
        with self._sf() as s:
            return s.get(KnowledgeNode, node_id)

    def list_by_subject(self, subject: str) -> list[KnowledgeNode]:
        with self._sf() as s:
            return list(s.query(KnowledgeNode).filter_by(subject=subject).all())
