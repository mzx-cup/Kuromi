"""SQLAlchemy model for AgentBehaviorLog (Slice S0 / S3).

This table is created in S0.3 so S3 can wire up real DB insert without
worrying about schema migration.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, JSON
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
    )

    def __init__(
        self,
        agent_id: str,
        user_id: str,
        action_type: str,
        input_summary: str = "",
        output_text: str = "",
        citations: Optional[list] = None,
    ) -> None:
        self.agent_id = agent_id
        self.user_id = user_id
        self.action_type = action_type
        self.input_summary = input_summary
        self.output_text = output_text
        self.citations = citations