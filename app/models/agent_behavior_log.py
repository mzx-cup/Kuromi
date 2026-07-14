"""SQLAlchemy model for AgentBehaviorLog (Slice S0 / S3).

This table is created in S0.3 so S3 can wire up real DB insert without
worrying about schema migration.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, JSON, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentBehaviorLog(Base):
    """A single agent-behavior record. Written first to DB; if DB fails,
    deferred to Redis; if Redis fails, deferred to disk; if disk fails,
    rejected (the caller gets the LogResult and may retry)."""
    __tablename__ = "agent_behavior_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    input_summary: Mapped[str] = mapped_column(Text, default="")
    output_text: Mapped[str] = mapped_column(Text, default="")
    citations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    hallucination_risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    block_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
    )

    # NOTE: no custom __init__ is defined. SQLAlchemy generates one from
    # the ``Mapped[...]`` annotations above; it accepts ``**kwargs`` and
    # applies mapped defaults (e.g. ``default=datetime.utcnow``) at flush
    # time. Custom constructors would shadow this and break
    # ``AgentBehaviorLog(**dict)`` patterns used by S3.2's real DB wiring.