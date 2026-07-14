"""SemanticMemory + MemoryConsolidationJob ORM repositories (slice-s6).

Both repos mirror the no-arg ``OrmEpisodicMemoryRepository`` pattern from
``app.repositories.orm.episodic_memory``: a module-level ``SessionFactory``
shared with the L1 and L2 repos, lazy table creation on first use, and
``reset_session_factory()`` (re-exported from ``knowledge_node``) for tests
that pin an isolated SQLite path.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.models.semantic_memory import SemanticMemory  # noqa: F401  (register table)
from app.models.memory_consolidation_job import MemoryConsolidationJob  # noqa: F401  (register table)
from app.repositories.orm.knowledge_node import (
    SessionFactory,
    reset_session_factory,
)


__all__ = [
    "OrmSemanticMemoryRepository",
    "OrmMemoryConsolidationJobRepository",
    "SessionFactory",
    "reset_session_factory",
]


class OrmSemanticMemoryRepository:
    """Sync SQLAlchemy repository for ``SemanticMemory`` rows.

    ``find_similar`` is a **placeholder** for S6.3 — it returns every
    active semantic row for the user, leaving the pattern-vs-row match
    decision to the consolidator's reinforce / weaken heuristic. The real
    similarity matching (embedding-based or LLM-judged) will replace this
    in a follow-up slice.
    """

    def __init__(self) -> None:
        self._sf = SessionFactory

    def insert(self, semantic: SemanticMemory) -> int:
        """Insert and return the new row's id."""
        with self._sf() as s:
            s.add(semantic)
            s.commit()
            return semantic.id

    def find_similar(
        self, *, user_id: str, statement: str,
    ) -> list[SemanticMemory]:
        """Return the user's active semantic memories.

        S6.3 placeholder: ignores ``statement`` and returns all rows for
        the user. Consolidator picks reinforce / weaken by inspecting
        pattern confidence. ``statement`` is accepted for forward
        compatibility with the similarity-matching implementation.
        """
        with self._sf() as s:
            rows = (
                s.query(SemanticMemory)
                .filter_by(user_id=user_id)
                .all()
            )
            return list(rows)

    def get(self, semantic_id: int) -> Optional[SemanticMemory]:
        with self._sf() as s:
            return s.get(SemanticMemory, semantic_id)

    def update_fields(
        self, semantic_id: int, fields: dict,
    ) -> int:
        """Apply a partial update (status / confidence / evidence_ids / last_reinforced_at).

        Returns the rowcount.
        """
        with self._sf() as s:
            updated = (
                s.query(SemanticMemory)
                .filter_by(id=semantic_id)
                .update(fields, synchronize_session=False)
            )
            s.commit()
            return int(updated)


class OrmMemoryConsolidationJobRepository:
    """Sync SQLAlchemy repository for consolidation-job ledger rows."""

    def __init__(self) -> None:
        self._sf = SessionFactory

    def insert(self, job: MemoryConsolidationJob) -> int:
        with self._sf() as s:
            s.add(job)
            s.commit()
            return job.id

    def update(self, job: MemoryConsolidationJob) -> int:
        """Persist status / error / finished_at on an already-fetched job."""
        with self._sf() as s:
            updated = (
                s.query(MemoryConsolidationJob)
                .filter_by(id=job.id)
                .update(
                    {
                        "status": job.status,
                        "error": job.error,
                        "finished_at": job.finished_at,
                    },
                    synchronize_session=False,
                )
            )
            s.commit()
            return int(updated)
