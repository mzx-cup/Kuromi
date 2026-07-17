"""S7 — Supervision SQLAlchemy models (L3 supervision layer).

Two tables back the supervision engine:

``SupervisionRule``
  A configurable rule with a DSL trigger, an ordered escalation chain,
  and a per-rule cooldown. The configuration surface is JSON-only — the
  DSL is a string, ``context_keys`` is an array of strings, and
  ``escalation_chain`` is a JSON document shaped like
  ``{"steps": [{"step": 1, "delay_hours": 0, "channels": ["inapp"],
                "template": "..."}, ...]}``.

``SupervisionEvent``
  An audit row written every time a rule fires. Tracks the current
  escalation step, the time of last step-advance, the firing timestamp,
  and the resolution status (``fired`` → ``responded`` / ``expired`` /
  ``cancelled``).

Naming note: ``metadata_`` (not ``metadata``) avoids colliding with
SQLAlchemy's reserved declarative attribute.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SupervisionRule(Base):
    """A supervision rule with a DSL trigger and an escalation chain."""
    __tablename__ = "supervision_rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    trigger_dsl: Mapped[str] = mapped_column(Text, nullable=False, default="")
    context_keys: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list,
    )
    cooldown_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    escalation_chain: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
    )


class SupervisionEvent(Base):
    """A triggered supervision rule — one row per escalation cycle."""
    __tablename__ = "supervision_events"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
        index=True,
    )
    last_step_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata_", JSON, nullable=False, default=dict,
    )


__all__ = ["SupervisionRule", "SupervisionEvent"]
