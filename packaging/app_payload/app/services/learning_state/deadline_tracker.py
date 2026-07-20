"""DeadlineTracker service — add_deadline + list_active + mark_done."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.models.deadline import DeadlineTracker
from app.repositories.orm.deadline import OrmDeadlineRepository


def add_deadline(
    user_id: str,
    title: str,
    due_at: datetime,
    *,
    supervised_by_rule_id: Optional[str] = None,
) -> int:
    """Record a new deadline for the user and return its id."""
    repo = OrmDeadlineRepository()
    entry = DeadlineTracker(
        user_id=user_id,
        title=title,
        due_at=due_at,
        status="pending",
        supervised_by_rule_id=supervised_by_rule_id,
    )
    return repo.insert(entry)


def list_active(user_id: str) -> list[dict]:
    """Return pending deadlines for the user, ordered by due_at ascending."""
    repo = OrmDeadlineRepository()
    return repo.list_active(user_id=user_id)


def mark_done(deadline_id: int) -> bool:
    """Mark a deadline as done; return True if a row was updated."""
    repo = OrmDeadlineRepository()
    return repo.mark_done(deadline_id=deadline_id)