"""SQLAlchemy models for learning statistics and history."""
from __future__ import annotations

from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Date, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class StudySession(Base):
    """One learning session record (replaces db.py study_sessions)."""
    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(64), default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    session_date: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())


class LearningRecord(Base):
    """Granular learning activity record (replaces db.py learning_records)."""
    __tablename__ = "learning_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    activity_type: Mapped[str] = mapped_column(String(64), default="study")
    subject: Mapped[str] = mapped_column(String(64), default="")
    minutes: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())


class UserStats(Base):
    """Aggregated user stats cached view (mirrors db.py user_stats.stats_json)."""
    __tablename__ = "user_stats"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    total_minutes: Mapped[int] = mapped_column(Integer, default=0)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    completed_courses: Mapped[int] = mapped_column(Integer, default=0)
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())


class LearningGoal(Base):
    """User-set learning goal (replaces db.py learning_goals)."""
    __tablename__ = "learning_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    target_value: Mapped[float] = mapped_column(Float, default=0)
    current_value: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(32), default="minutes")
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())


class WeeklySummary(Base):
    """Weekly summary record."""
    __tablename__ = "weekly_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    week_start: Mapped[date] = mapped_column(Date)
    total_minutes: Mapped[int] = mapped_column(Integer, default=0)
    subjects: Mapped[dict] = mapped_column(JSON, default=dict)
