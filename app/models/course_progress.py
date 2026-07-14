"""SQLAlchemy models for course progress and learning paths.

This slice (M5) introduces per-user learning state. The existing
``app/models/course.py`` already models course CONTENT (subjects,
chapters, slides). The models here model per-user PROGRESS through
that content.
"""
from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Date, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CourseProgress(Base):
    """User's progress on a single course (replaces db.py course_progress)."""
    __tablename__ = "course_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    progress_percent: Mapped[float] = mapped_column(Float, default=0)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_accessed: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())
    state_json: Mapped[dict] = mapped_column(JSON, default=dict)


class LearningPath(Base):
    """A personalized learning path for a user (replaces db.py learning_path)."""
    __tablename__ = "learning_paths"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())


class LearningPathNode(Base):
    """A node (course or topic) within a learning path."""
    __tablename__ = "learning_path_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    path_id: Mapped[int] = mapped_column(Integer, ForeignKey("learning_paths.id"), nullable=False, index=True)
    course_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(default=False)


class UserEvaluation(Base):
    """A user assessment/evaluation (replaces db.py user_evaluations).

    The legacy table includes a number of metric columns
    (interaction_count, socratic_pass_rate, etc.). In M5 we only
    model the minimum required for repository parity; richer
    columns can be added later without breaking the read contract.
    """
    __tablename__ = "user_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(64), default="")
    score: Mapped[float] = mapped_column(Float, default=0)
    max_score: Mapped[float] = mapped_column(Float, default=100)
    notes: Mapped[str] = mapped_column(Text, default="")
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())


class CourseGenerationStatus(Base):
    """Track async course generation status (replaces db.py course_generation_status)."""
    __tablename__ = "course_generation_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    progress_percent: Mapped[float] = mapped_column(Float, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CourseDeadline(Base):
    """A deadline for a course (assignment / exam / project).

    Used by ``CourseProgressRepository.get_upcoming_deadlines`` to surface
    upcoming work to the tutor engine.
    """
    __tablename__ = "course_deadlines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    deadline: Mapped[date] = mapped_column(Date, nullable=False, index=True)


class DailyRoute(Base):
    """Per-user daily task route (replaces db.py daily_routes).

    One row per (user_id, route_date). ``tasks_json`` holds the suggested
    tasks for the day; ``completed_json`` holds the completed-subset markers
    used by the rule engine / dashboard widgets.
    """
    __tablename__ = "daily_routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    route_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tasks_json: Mapped[list] = mapped_column(JSON, default=list)
    completed_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())
