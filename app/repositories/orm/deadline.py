"""DeadlineTracker ORM Repository — L4 learning-state layer (slice-s4).

Mirrors the S1.4 ``OrmKnowledgeRepository`` pattern at
``app/repositories/orm/knowledge_node.py``: module-level sync engine,
``SessionFactory`` shared with the L1 repo, and a no-arg constructor.

Reuses the L1 repo's ``SessionFactory`` and ``_to_sync_url`` so the L4
write path points at the same database without re-deriving the URL.
Tests can call ``reset_session_factory()`` (imported from
``app.repositories.orm.knowledge_node``) to rebuild the engine.
"""
from __future__ import annotations

from typing import Optional

from app.models.deadline import DeadlineTracker  # noqa: F401  (register table on Base.metadata)
from app.repositories.orm.knowledge_node import (
    SessionFactory,
    reset_session_factory,
)


class OrmDeadlineRepository:
    """Sync SQLAlchemy repository for L4 ``DeadlineTracker``.

    No-arg constructor — uses the shared module-level ``SessionFactory``
    so call sites can simply do ``OrmDeadlineRepository().insert(entry)``
    without threading a session through every invocation.
    """
    def __init__(self) -> None:
        self._sf = SessionFactory

    def insert(self, entry: DeadlineTracker) -> int:
        with self._sf() as s:
            s.add(entry)
            s.commit()
            return entry.id

    def list_active(self, *, user_id: str) -> list[dict]:
        with self._sf() as s:
            rows = (
                s.query(DeadlineTracker)
                .filter_by(user_id=user_id, status="pending")
                .order_by(DeadlineTracker.due_at.asc())
                .all()
            )
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "due_at": r.due_at,
                    "status": r.status,
                    "supervised_by_rule_id": r.supervised_by_rule_id,
                }
                for r in rows
            ]

    def mark_done(self, deadline_id: int) -> bool:
        with self._sf() as s:
            updated = (
                s.query(DeadlineTracker)
                .filter(DeadlineTracker.id == deadline_id)
                .update({"status": "done"})
            )
            s.commit()
            return bool(updated)