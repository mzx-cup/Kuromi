"""SQLAlchemy implementation for chat (Slice #9).

This repository backs the chat read path with SQLAlchemy. It mirrors the
methods on :class:`app.repositories.legacy.chat.DbPyChatRepository`
so callers can swap implementations behind the
:class:`app.repositories.base.ChatRepository` Protocol.

The ORM writes ``msg_metadata`` (JSON) directly via SQLAlchemy's JSON
column type — no legacy ``metadata`` TEXT column is involved.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, UserMemory


class SqlAlchemyChatRepository:
    def __init__(self, session: Session = None):
        self.session = session

    # ── messages ──

    def save_message(self, user_id: str, message: dict) -> int:
        msg = ChatMessage(
            user_id=user_id,
            role=message.get("role", "user"),
            content=message.get("content", ""),
            msg_metadata=message.get("metadata", {}),
            created_at=datetime.utcnow(),
        )
        self.session.add(msg)
        self.session.flush()
        return msg.id

    def get_history(self, user_id: str, limit: int = 50) -> list:
        msgs = (
            self.session.query(ChatMessage)
            .filter_by(user_id=user_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "metadata": m.msg_metadata or {},
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in reversed(msgs)
        ]

    # ── memories ──

    def save_memory(self, user_id: str, memory: dict) -> int:
        mem = UserMemory(
            user_id=user_id,
            memory_type=memory.get("memory_type", "fact"),
            content=memory.get("content", ""),
            importance=memory.get("importance", 1),
            source_conversation_id=memory.get("source_conversation_id"),
            created_at=datetime.utcnow(),
        )
        self.session.add(mem)
        self.session.flush()
        return mem.id

    def get_memories(self, user_id: str, memory_type: str | None = None, limit: int = 20) -> list:
        query = self.session.query(UserMemory).filter_by(user_id=user_id)
        if memory_type is not None:
            query = query.filter_by(memory_type=memory_type)
        mems = (
            query
            .order_by(UserMemory.importance.desc(), UserMemory.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": m.id,
                "memory_type": m.memory_type,
                "content": m.content,
                "importance": m.importance,
                "source_conversation_id": m.source_conversation_id,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "last_accessed": m.last_accessed.isoformat() if m.last_accessed else None,
                "confirmed": m.confirmed,
                "access_count": m.access_count,
            }
            for m in mems
        ]

    def update_memory(self, memory_id: int, updates: dict) -> None:
        mem = self.session.query(UserMemory).filter_by(id=memory_id).first()
        if mem:
            if "content" in updates:
                mem.content = updates["content"]
            if "importance" in updates:
                mem.importance = updates["importance"]
            self.session.flush()

    def confirm_memory(self, memory_id: int, confirmed: bool = True) -> None:
        mem = self.session.query(UserMemory).filter_by(id=memory_id).first()
        if mem:
            mem.confirmed = 1 if confirmed else 0
            self.session.flush()

    def delete_memory(self, memory_id: int) -> None:
        mem = self.session.query(UserMemory).filter_by(id=memory_id).first()
        if mem:
            self.session.delete(mem)
            self.session.flush()

    def bump_memory_access(self, memory_id: int) -> None:
        mem = self.session.query(UserMemory).filter_by(id=memory_id).first()
        if mem:
            mem.access_count = (mem.access_count or 0) + 1
            mem.last_accessed = datetime.utcnow()
            self.session.flush()