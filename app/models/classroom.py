"""SQLAlchemy models for classroom sessions, quiz records, and agent turns (M10).

Slice #10 extends the existing models with extra fields needed by the
:class:`app.repositories.orm.classroom.SqlAlchemyClassroomRepository`
mirror of :class:`app.repositories.legacy.classroom.DbPyClassroomRepository`.

Existing fields are kept untouched (the ``ClassroomSession.id`` is still
``String(64)`` and uses ``student_id`` per the immersive-classroom
implementation). New optional fields are added with sensible defaults so
the repository can read/write legacy-style data without breaking callers
that already depend on the prior schema.

NOTE: do not rename or remove the existing columns — only add new ones.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ClassroomSession(Base):
    __tablename__ = "classroom_sessions"

    # Original (immersive-classroom) schema — kept intact.
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
    teacher_persona: Mapped[str] = mapped_column(
        String(32), default="expert_mentor", nullable=False,
        comment="AI教师角色: patient_tutor|socratic_questioner|energetic_lecturer|expert_mentor"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # M10 extensions (additive only, no rename / no removal).
    # The original ``id`` PK is String(64) (UUID-style), but the legacy
    # ``classroom_sessions`` table in db.py uses ``id INTEGER``. The ORM
    # repository works with whatever id the caller passes, and the new
    # ``user_id`` column mirrors the legacy schema's PK-to-user mapping.
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    current_slide: Mapped[int] = mapped_column(Integer, default=0)
    teacher_mode: Mapped[bool] = mapped_column(Boolean, default=False)


class QuizRecord(Base):
    __tablename__ = "quiz_records"

    # Original schema — kept intact.
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

    # M10 extensions (additive only).
    # Mirror legacy ``quiz_records`` columns: session_id, user_id, question,
    # answer, correct, max_score. All default-friendly to avoid breaking
    # existing inserts that only populate the original columns.
    session_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    correct: Mapped[bool] = mapped_column(Boolean, default=False)
    max_score: Mapped[float] = mapped_column(Float, default=100.0)


class AgentTurnRecord(Base):
    __tablename__ = "agent_turn_records"

    # Original schema — kept intact.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    classroom_id: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(64), default="")
    agent_role: Mapped[str] = mapped_column(String(64), default="")
    turn_index: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text, default="")
    actions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # M10 extensions (additive only).
    # Mirror legacy ``classroom_agent_turns``: session_id, turn_number,
    # user_input, agent_output. ``session_id`` is a string to match the
    # ``classroom_sessions.id`` PK type in this ORM.
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    turn_number: Mapped[int] = mapped_column(Integer, default=0)
    user_input: Mapped[str] = mapped_column(Text, default="")
    agent_output: Mapped[str] = mapped_column(Text, default="")
