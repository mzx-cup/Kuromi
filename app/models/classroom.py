from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ClassroomSession(Base):
    __tablename__ = "classroom_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(String(64), nullable=False)
    course_id: Mapped[str] = mapped_column(String(64), default="")
    course_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    current_scene_index: Mapped[int] = mapped_column(Integer, default=0)
    visited_scenes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    quiz_answers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    chat_history: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    time_spent: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class QuizRecord(Base):
    __tablename__ = "quiz_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    classroom_id: Mapped[str] = mapped_column(String(64), nullable=False)
    student_id: Mapped[str] = mapped_column(String(64), nullable=False)
    quiz_id: Mapped[str] = mapped_column(String(64), default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    answers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    feedback: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AgentTurnRecord(Base):
    __tablename__ = "agent_turn_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    classroom_id: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(64), default="")
    agent_role: Mapped[str] = mapped_column(String(64), default="")
    turn_index: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text, default="")
    actions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
