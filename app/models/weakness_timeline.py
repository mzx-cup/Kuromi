"""WeaknessTimeline SQLAlchemy model — L4 learning-state layer (slice-s4).

A WeaknessTimeline is a single weakness-snapshot for a user on a given
dimension at a point in time. Downstream consumers:
  - S5 memory consolidation (EpisodicMemory)
  - S9 SocraticAgent memory card

Dimensions (L4 taxonomy):
  - "knowledge_base"    — mastery score of concept clusters
  - "cognitive_focus"   — sustained attention metric
  - "engagement"        — session frequency / completion rate
  - "recall_retention"  — SM2 retention rate
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Float, JSON, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class WeaknessTimeline(Base):
    """A single weakness-snapshot for a user on a given dimension.

    Dimensions (L4 taxonomy):
      - "knowledge_base" — mastery score of concept clusters
      - "cognitive_focus" — sustained attention metric
      - "engagement" — session frequency / completion rate
      - "recall_retention" — SM2 retention rate
    """
    __tablename__ = "weakness_timelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dim: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 (weak) → 1.0 (strong)
    evidence_kb_nodes: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
        index=True,
    )
