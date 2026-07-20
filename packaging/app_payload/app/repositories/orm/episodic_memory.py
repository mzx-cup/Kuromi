"""EpisodicMemory ORM Repository — L2 memory layer (slice-s5).

Mirrors the S1.4 ``OrmKnowledgeRepository`` pattern at
``app/repositories/orm/knowledge_node.py``: module-level sync engine,
``SessionFactory`` shared with the L1 repo, and a no-arg constructor.

Reuses the L1 repo's ``SessionFactory`` and ``_to_sync_url`` so the L2
write path points at the same database without re-deriving the URL.
Tests can call ``reset_session_factory()`` (imported from
``app.repositories.orm.knowledge_node``) to rebuild the engine.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from app.models.episodic_memory import EpisodicMemory  # noqa: F401  (register table on Base.metadata)
from app.repositories.orm.knowledge_node import (
    SessionFactory,
    reset_session_factory,
)


class OrmEpisodicMemoryRepository:
    """Sync SQLAlchemy repository for L2 ``EpisodicMemory``.

    No-arg constructor — uses the shared module-level ``SessionFactory``
    so call sites can simply do ``OrmEpisodicMemoryRepository().insert(entry)``
    without threading a session through every invocation.
    """
    def __init__(self) -> None:
        self._sf = SessionFactory

    def insert(self, entry: EpisodicMemory) -> int:
        with self._sf() as s:
            s.add(entry)
            s.commit()
            return entry.id

    def recent_unconsolidated(
        self, *, user_id: str, days: int = 7,
    ) -> list[EpisodicMemory]:
        """Return episodes for ``user_id`` created in the last ``days`` days
        that have not yet been consolidated (``consolidated_into IS NULL``).

        Ordered by ``created_at`` ascending (chronological).
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        with self._sf() as s:
            rows = (
                s.query(EpisodicMemory)
                .filter_by(user_id=user_id)
                .filter(EpisodicMemory.consolidated_into.is_(None))
                .filter(EpisodicMemory.created_at >= cutoff)
                .order_by(EpisodicMemory.created_at.asc())
                .all()
            )
            return list(rows)

    def mark_consolidated(
        self, episode_ids: list[int], semantic_id: int,
    ) -> int:
        """Bulk-set ``consolidated_into = semantic_id`` for the given ids.

        Returns the rowcount. Uses a one-shot UPDATE so the L2
        consolidation pass can mark a batch of episodes in a single
        round-trip rather than N individual writes.
        """
        if not episode_ids:
            return 0
        with self._sf() as s:
            updated = (
                s.query(EpisodicMemory)
                .filter(EpisodicMemory.id.in_(episode_ids))
                .update(
                    {"consolidated_into": semantic_id},
                    synchronize_session=False,
                )
            )
            s.commit()
            return int(updated)