"""S7 — SupervisionRule + SupervisionEvent ORM repositories.

Both repos mirror the no-arg ``OrmEpisodicMemoryRepository`` pattern: a
module-level ``SessionFactory`` shared with the L1 / L2 / L4 repos
(imported from ``knowledge_node``), lazy table creation on first use,
and ``reset_session_factory()`` (re-exported from ``knowledge_node``)
for tests that pin an isolated SQLite path.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from app.models.supervision import SupervisionEvent, SupervisionRule  # noqa: F401  (register tables)
from app.repositories.orm.knowledge_node import (
    SessionFactory,
    reset_session_factory,
)


__all__ = [
    "OrmSupervisionRuleRepository",
    "OrmSupervisionEventRepository",
    "SessionFactory",
    "reset_session_factory",
]


class OrmSupervisionRuleRepository:
    """Sync SQLAlchemy repository for ``SupervisionRule`` rows."""

    def __init__(self) -> None:
        self._sf = SessionFactory

    def insert(self, rule: SupervisionRule) -> str:
        with self._sf() as s:
            s.add(rule)
            s.commit()
            return rule.id

    def get(self, rule_id: str) -> Optional[SupervisionRule]:
        with self._sf() as s:
            return s.get(SupervisionRule, rule_id)

    def list_enabled(self) -> list[SupervisionRule]:
        with self._sf() as s:
            rows = (
                s.query(SupervisionRule)
                .filter_by(enabled=True)
                .order_by(SupervisionRule.priority.asc())
                .all()
            )
            return list(rows)

    def count_all(self) -> int:
        with self._sf() as s:
            return int(s.query(SupervisionRule).count())


class OrmSupervisionEventRepository:
    """Sync SQLAlchemy repository for ``SupervisionEvent`` rows."""

    def __init__(self) -> None:
        self._sf = SessionFactory

    def insert(self, event: SupervisionEvent) -> int:
        with self._sf() as s:
            s.add(event)
            s.commit()
            return event.id

    def update(self, event: SupervisionEvent) -> int:
        """Persist mutable fields of an already-fetched event."""
        with self._sf() as s:
            updated = (
                s.query(SupervisionEvent)
                .filter_by(id=event.id)
                .update(
                    {
                        "status": event.status,
                        "current_step": event.current_step,
                        "last_step_at": event.last_step_at,
                        "responded_at": event.responded_at,
                        "metadata_": event.metadata_,
                    },
                    synchronize_session=False,
                )
            )
            s.commit()
            return int(updated)

    def list_pending_for_user(self, user_id: str) -> list[SupervisionEvent]:
        with self._sf() as s:
            rows = (
                s.query(SupervisionEvent)
                .filter_by(user_id=user_id)
                .filter(SupervisionEvent.status.in_(("pending", "fired")))
                .order_by(SupervisionEvent.fired_at.desc())
                .all()
            )
            return list(rows)

    def list_due_for_step_advance(self, *, now: datetime) -> list[SupervisionEvent]:
        """Return fired events whose ``last_step_at`` is overdue for step advance."""
        with self._sf() as s:
            rows = (
                s.query(SupervisionEvent)
                .filter_by(status="fired")
                .filter(SupervisionEvent.last_step_at.isnot(None))
                .filter(SupervisionEvent.last_step_at <= now)
                .all()
            )
            return list(rows)

    def recent_for_user_rule(
        self,
        *,
        user_id: str,
        rule_id: str,
        within_hours: int,
        now: datetime,
    ) -> list[SupervisionEvent]:
        """Return non-terminal events for ``(user_id, rule_id)`` within window."""
        cutoff = now - timedelta(hours=within_hours)
        with self._sf() as s:
            rows = (
                s.query(SupervisionEvent)
                .filter_by(user_id=user_id, rule_id=rule_id)
                .filter(SupervisionEvent.fired_at >= cutoff)
                .filter(SupervisionEvent.status.in_(("pending", "fired")))
                .all()
            )
            return list(rows)
