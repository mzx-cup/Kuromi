"""SQLAlchemy models for focus session tracking and flow score history (M7).

This slice introduces normalized focus session storage backing the flow
score / focus analysis feature in the hub dashboard. Three tables:

* ``focus_sessions``       – a single focus/work session
* ``focus_events``         – events within a session (distraction, switch, etc.)
* ``user_focus_history``   – aggregated focus history per user per day

The repository only persists events and aggregates; the flow score
formula itself continues to live in higher-level services (see
``app/services/dashboard_data.py``).
"""
from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Date, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FocusSession(Base):
    """A single focus/work session (replaces db.py focus_sessions)."""
    __tablename__ = "focus_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    planned_minutes: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(default=False)
    subject: Mapped[str] = mapped_column(String(64), default="")


class FocusEvent(Base):
    """An event within a focus session (distraction, switch, etc.)."""
    __tablename__ = "focus_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("focus_sessions.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), default="start")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())
    flow_score: Mapped[float] = mapped_column(Float, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class UserFocusHistory(Base):
    """Aggregated focus history per user per day (replaces db.py user_focus_history)."""
    __tablename__ = "user_focus_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    focus_date: Mapped[date] = mapped_column(Date, default=date.today)
    total_focus_minutes: Mapped[int] = mapped_column(Integer, default=0)
    sessions_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_flow_score: Mapped[float] = mapped_column(Float, default=0)
    deep_focus_minutes: Mapped[int] = mapped_column(Integer, default=0)