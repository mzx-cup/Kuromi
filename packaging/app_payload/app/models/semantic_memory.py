"""SemanticMemory SQLAlchemy model — L2 consolidation product (slice-s6).

A SemanticMemory row is the long-lived, confidence-scored artefact produced
by the S6 consolidation pipeline. It wraps a cluster of related
EpisodicMemory rows behind a single declarative ``statement`` and walks
through three lifecycle stages driven by ``app.services.memory.lifecycle``:
``active`` → ``fading`` → ``retired``. Fresh evidence (``reinforce``) can
reactivate a fading row, while long idleness (90d / 180d) demotes it
through the stages.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from sqlalchemy import String, Text, JSON, DateTime, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.services.memory.lifecycle import ACTIVE


class SemanticMemory(Base):
    """A consolidated semantic memory distilled from a cluster of episodes.

    Downstream consumers:
      - Memory-card injection in SocraticAgent (S9) reads active rows.
      - The cron consolidator (S6.3) reinforces / weakens / retires them.
    """
    __tablename__ = "semantic_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ACTIVE,
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    evidence_ids: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list,
    )
    last_reinforced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),  # naive UTC to match lifecycle.compare
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),  # naive UTC to match lifecycle.compare
    )


__all__ = ["SemanticMemory"]
