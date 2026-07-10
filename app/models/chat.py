"""SQLAlchemy models for chat messages, conversation summaries, agent turns, and memories.

Slice #9 introduces a dedicated chat schema (msg_metadata JSON, integer user_id
FK) on top of the broader, session-oriented Message/ConversationSummary
definitions that already live in ``app.models.message`` and
``app.models.classroom``.

The classes here are intentionally distinct from those to avoid colliding
SQLAlchemy table definitions during test setup. They back the new
:class:`app.repositories.orm.chat.SqlAlchemyChatRepository`.

NOTE: the JSON column is named ``msg_metadata`` (NOT ``metadata``) because
``metadata`` is reserved by SQLAlchemy's declarative ``Base``.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ChatMessage(Base):
    """A single chat message (Slice #9 — replaces db.py messages row-by-row)."""
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id"), nullable=False, index=True,
    )
    role: Mapped[str] = mapped_column(String(32), default="user")
    content: Mapped[str] = mapped_column(Text, default="")
    msg_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
    )


class ChatSummary(Base):
    """Summary of a conversation (Slice #9 — replaces db.py conversation_summaries)."""
    __tablename__ = "chat_conversation_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id"), nullable=False, index=True,
    )
    conversation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    key_facts: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
    )


class ChatTurnRecord(Base):
    """Record of one turn in an agent interaction (Slice #9 — replaces db.py agent_turn_records)."""
    __tablename__ = "chat_agent_turn_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id"), nullable=False, index=True,
    )
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, default=0)
    user_input: Mapped[str] = mapped_column(Text, default="")
    agent_output: Mapped[str] = mapped_column(Text, default="")
    tool_calls: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
    )


class UserMemory(Base):
    """Long-term user memory extracted from conversations (Slice #9 — replaces db.py user_memories)."""
    __tablename__ = "user_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id"), nullable=False, index=True,
    )
    memory_type: Mapped[str] = mapped_column(String(32), default="fact")  # fact/preference/goal
    content: Mapped[str] = mapped_column(Text, default="")
    importance: Mapped[int] = mapped_column(Integer, default=1)
    source_conversation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
    )
    last_accessed: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )