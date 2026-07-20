"""db.py wrapper for chat messages, summaries, agent turns, and memories.

Provides read/write methods against the db.py tables
``messages``, ``conversation_summaries``, ``agent_turn_records`` and
``user_memories``. Mirrors
:class:`app.repositories.orm.chat.SqlAlchemyChatRepository` so callers
can swap implementations behind the
:class:`app.repositories.base.ChatRepository` Protocol.

NOTE: the ``messages`` table uses the new ``msg_metadata`` column name
(not the legacy ``metadata``). Production data must be migrated with
``scripts/migrate_messages_metadata.py`` before this repository is
considered safe to read.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime

import db


class DbPyChatRepository:
    def __init__(self, db_path: str = None):
        # Absolute path from ``db.py`` so legacy reads follow the same
        # SQLite file the rest of the project uses, regardless of CWD.
        import db as _db
        self.db_path = db_path or _db.SQLITE_PATH

    def _conn(self):
        return sqlite3.connect(self.db_path)

    # ── messages ──

    def save_message(self, user_id, message: dict) -> int:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO messages (user_id, role, content, msg_metadata, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                message.get("role", "user"),
                message.get("content", ""),
                json.dumps(message.get("metadata", {}), ensure_ascii=False),
                datetime.now().isoformat(),
            ))
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def get_history(self, user_id, limit: int = 50) -> list:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, role, content, msg_metadata, created_at
                FROM messages
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            rows = [
                {
                    "id": r[0],
                    "role": r[1],
                    "content": r[2],
                    "metadata": json.loads(r[3]) if r[3] else {},
                    "created_at": r[4],
                }
                for r in cur.fetchall()
            ][::-1]  # reverse to chronological order
            return rows
        finally:
            conn.close()

    # ── memories ──

    def save_memory(self, user_id, memory: dict) -> int:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO user_memories
                (user_id, memory_type, content, importance, source_conversation_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                memory.get("memory_type", "fact"),
                memory.get("content", ""),
                memory.get("importance", 1),
                memory.get("source_conversation_id"),
                datetime.now().isoformat(),
            ))
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def get_memories(self, user_id, memory_type: str | None = None, limit: int = 20) -> list:
        conn = self._conn()
        try:
            cur = conn.cursor()
            if memory_type is not None:
                cur.execute("""
                    SELECT id, memory_type, content, importance, source_conversation_id,
                           created_at, last_accessed
                    FROM user_memories
                    WHERE user_id = ? AND memory_type = ?
                    ORDER BY importance DESC, created_at DESC
                    LIMIT ?
                """, (user_id, memory_type, limit))
            else:
                cur.execute("""
                    SELECT id, memory_type, content, importance, source_conversation_id,
                           created_at, last_accessed
                    FROM user_memories
                    WHERE user_id = ?
                    ORDER BY importance DESC, created_at DESC
                    LIMIT ?
                """, (user_id, limit))
            return [
                {
                    "id": r[0],
                    "memory_type": r[1],
                    "content": r[2],
                    "importance": r[3],
                    "source_conversation_id": r[4],
                    "created_at": r[5],
                    "last_accessed": r[6],
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

    def update_memory(self, memory_id: int, updates: dict) -> None:
        assignments = []
        values = []
        if "content" in updates:
            assignments.append("content = ?")
            values.append(updates["content"])
        if "importance" in updates:
            assignments.append("importance = ?")
            values.append(updates["importance"])
        if not assignments:
            return

        conn = self._conn()
        try:
            conn.execute(
                f"UPDATE user_memories SET {', '.join(assignments)} WHERE id = ?",
                (*values, memory_id),
            )
            conn.commit()
        finally:
            conn.close()

    def confirm_memory(self, memory_id: int, confirmed: bool = True) -> None:
        db.confirm_user_memory(memory_id, confirmed)

    def delete_memory(self, memory_id: int) -> None:
        db.delete_user_memory(memory_id)

    def bump_memory_access(self, memory_id: int) -> None:
        db.bump_memory_access(memory_id)