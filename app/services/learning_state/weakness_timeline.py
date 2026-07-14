"""WeaknessTimeline service — record and query snapshots of user weakness."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from app.models.weakness_timeline import WeaknessTimeline
from app.repositories.orm.weakness_timeline import OrmWeaknessTimelineRepository


def record_snapshot(
    user_id: str,
    dim: str,
    score: float,
    evidence_kb_nodes: Optional[list[str]] = None,
) -> int:
    """Record a weakness-snapshot for the user on a given dimension.

    Returns the new id.
    """
    repo = OrmWeaknessTimelineRepository()
    entry = WeaknessTimeline(
        user_id=user_id,
        dim=dim,
        score=score,
        evidence_kb_nodes=evidence_kb_nodes or [],
    )
    return repo.insert(entry)


def recent(
    user_id: str,
    dim: str,
    within_days: int = 7,
) -> list[dict]:
    """Return snapshots for the user on a given dimension within the last N days.

    Returned dicts have keys: id, dim, score, evidence_kb_nodes, snapshot_at.
    Ordered most-recent first.
    """
    repo = OrmWeaknessTimelineRepository()
    return repo.recent(user_id=user_id, dim=dim, within_days=within_days)
