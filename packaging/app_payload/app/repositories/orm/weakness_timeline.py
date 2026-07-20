"""WeaknessTimeline ORM Repository — L4 learning-state layer (slice-s4).

Mirrors the S1.4 ``OrmKnowledgeRepository`` pattern at
``app/repositories/orm/knowledge_node.py``: module-level sync engine,
``SessionFactory`` shared with the L1 repo, and a no-arg constructor.

Reuses the L1 repo's ``SessionFactory`` and ``_to_sync_url`` so the L4
write path points at the same database without re-deriving the URL.
Tests can call ``reset_session_factory()`` (imported from
``app.repositories.orm.knowledge_node``) to rebuild the engine.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from app.models.weakness_timeline import WeaknessTimeline  # noqa: F401  (register table on Base.metadata)
from app.repositories.orm.knowledge_node import (
    SessionFactory,
    reset_session_factory,
)


class OrmWeaknessTimelineRepository:
    """Sync SQLAlchemy repository for L4 ``WeaknessTimeline``.

    No-arg constructor — uses the shared module-level ``SessionFactory``
    so call sites can simply do ``OrmWeaknessTimelineRepository().insert(entry)``
    without threading a session through every invocation.
    """
    def __init__(self) -> None:
        self._sf = SessionFactory

    def insert(self, entry: WeaknessTimeline) -> int:
        with self._sf() as s:
            s.add(entry)
            s.commit()
            return entry.id

    def recent(self, *, user_id: str, dim: str, within_days: int) -> list[dict]:
        cutoff = datetime.utcnow() - timedelta(days=within_days)
        with self._sf() as s:
            rows = (
                s.query(WeaknessTimeline)
                .filter_by(user_id=user_id, dim=dim)
                .filter(WeaknessTimeline.snapshot_at >= cutoff)
                .order_by(WeaknessTimeline.snapshot_at.desc())
                .all()
            )
            return [
                {
                    "id": r.id,
                    "dim": r.dim,
                    "score": r.score,
                    "evidence_kb_nodes": r.evidence_kb_nodes or [],
                    "snapshot_at": r.snapshot_at,
                }
                for r in rows
            ]
