"""EpisodicMemory SQLAlchemy model — L2 memory layer (slice-s5).

An EpisodicMemory is a single time-stamped event in a user's learning
journey (a Socratic turn, a quiz attempt, a session boundary, a KB
lookup, …). Episodes accumulate over time and are later clustered
into ``SemanticMemory`` rows during the S6 memory-consolidation pass.

Consolidation contract:
  - ``consolidated_into IS NULL`` → episode is **unconsolidated** and
    is eligible for the next consolidation run.
  - ``consolidated_into = <int>`` → episode has been absorbed into the
    SemanticMemory with that id (FK is soft until S6 lands).

event_type values (String(32)):
  - "conversation"  — a Socratic / tutor turn (S9 hook)
  - "quiz_attempt"  — a quiz submission with score
  - "session_start" — a learning session was opened
  - "session_end"   — a learning session was closed
  - "kb_lookup"     — a KB retrieval event (for retrieval-aware memory)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Text, JSON, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class EpisodicMemory(Base):
    """A single time-stamped learning event for a user.

    Downstream consumers:
      - S6 memory consolidation (clusters episodes into ``SemanticMemory``)
      - S9 SocraticAgent memory-card injection (reads recent unconsolidated)
    """
    __tablename__ = "episodic_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    event_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    consolidated_into: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
        index=True,
    )


__all__ = ["EpisodicMemory"]