"""MemoryConsolidationJob SQLAlchemy model — job ledger for the consolidator.

Every invocation of ``consolidate_user`` (S6.3) writes one row to this
table so the daily scheduler's progress, the input episode ids it
covered, and any failure trace are queryable for ops and debugging.
The job's status transitions ``running`` → ``done`` (or ``failed``).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from sqlalchemy import String, Text, JSON, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MemoryConsolidationJob(Base):
    """A single consolidation run's audit trail.

    Status field values (``String(16)``):
      - ``"running"`` — consolidator is iterating clusters.
      - ``"done"``    — all clusters processed successfully.
      - ``"failed"``  — at least one cluster raised; ``error`` holds the message.
    """
    __tablename__ = "memory_consolidation_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    episodic_input_ids: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list,
    )
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),  # naive UTC to match lifecycle.compare
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
    )


__all__ = ["MemoryConsolidationJob"]
