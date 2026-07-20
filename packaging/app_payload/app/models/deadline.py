"""DeadlineTracker SQLAlchemy model — L4 learning-state layer (slice-s4).

A DeadlineTracker is a user-facing deadline (e.g. "复习 Chapter 3 by Fri")
that the platform can surface to the user and, optionally, use as the
trigger for a supervision rule. Downstream consumers:
  - S7 supervision engine (fires the rule referenced by
    ``supervised_by_rule_id`` when the deadline approaches)
  - L5 decision layer (deadline-aware scheduling)

Schema:
  - id: int (PK, autoincrement)
  - user_id: str (indexed)
  - title: str (human-readable deadline label)
  - due_at: datetime (tz-aware, indexed)
  - status: str — "pending" / "done" / "overdue"
  - supervised_by_rule_id: Optional[str] — soft reference to a
    SupervisionRule id (e.g. "SUP-014" for 学习停滞提醒). The
    supervision table does not exist until S7, so this column is a
    plain String with no FK constraint; S7 will wire the FK once
    SupervisionRule is added.
  - created_at: datetime (tz-aware)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class DeadlineTracker(Base):
    """A user-facing deadline with optional supervision-rule binding.

    ``supervised_by_rule_id`` is a soft reference (no FK) until S7
    adds the SupervisionRule table.
    """
    __tablename__ = "deadlines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending",
    )
    supervised_by_rule_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True,
        # Soft reference to SupervisionRule (added in S7). No FK today.
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
    )


__all__ = ["DeadlineTracker"]