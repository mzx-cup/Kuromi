"""db.py wrapper for classroom sessions and quiz records (M10).

Provides read/write methods against the legacy ``classroom_sessions``,
``quiz_records`` and ``classroom_agent_turns`` tables.

Mirrors :class:`app.repositories.orm.classroom.SqlAlchemyClassroomRepository`
so callers can swap implementations behind the
:class:`app.repositories.base.ClassroomRepository` Protocol.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime


class DbPyClassroomRepository:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or "xingshi.db"

    def _conn(self):
        return sqlite3.connect(self.db_path)

    # ── sessions ──

    def get_session(self, session_id: int) -> dict | None:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, user_id, course_id, started_at, ended_at,
                       current_slide, status, teacher_mode
                FROM classroom_sessions WHERE id = ?
                """,
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "user_id": row[1],
                "course_id": row[2],
                "started_at": row[3],
                "ended_at": row[4],
                "current_slide": row[5] or 0,
                "status": row[6] or "active",
                "teacher_mode": bool(row[7]),
            }
        finally:
            conn.close()

    def list_sessions(self, user_id) -> list:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, course_id, started_at, ended_at, current_slide, status
                FROM classroom_sessions
                WHERE user_id = ?
                ORDER BY started_at DESC
                """,
                (user_id,),
            )
            return [
                {
                    "id": r[0],
                    "course_id": r[1],
                    "started_at": r[2],
                    "ended_at": r[3],
                    "current_slide": r[4] or 0,
                    "status": r[5] or "active",
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

    def create_session(self, user_id, course_id: str, teacher_mode: bool = False) -> int:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO classroom_sessions
                (user_id, course_id, started_at, status, teacher_mode)
                VALUES (?, ?, ?, 'active', ?)
                """,
                (user_id, course_id, datetime.now().isoformat(), 1 if teacher_mode else 0),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def update_session(self, session_id: int, updates: dict) -> None:
        conn = self._conn()
        try:
            cur = conn.cursor()
            sets = []
            values = []
            for k, v in updates.items():
                if k in ("current_slide", "status", "ended_at", "teacher_mode", "course_id"):
                    sets.append(f"{k} = ?")
                    if k == "teacher_mode":
                        values.append(1 if v else 0)
                    else:
                        values.append(v)
            if not sets:
                return
            values.append(session_id)
            cur.execute(
                f"UPDATE classroom_sessions SET {', '.join(sets)} WHERE id = ?",
                values,
            )
            conn.commit()
        finally:
            conn.close()

    # ── quiz records ──

    def save_quiz_record(self, user_id, quiz_data: dict) -> int:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO quiz_records
                (user_id, session_id, question, answer, correct, score,
                 max_score, passed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    quiz_data.get("session_id"),
                    quiz_data.get("question", ""),
                    quiz_data.get("answer", ""),
                    1 if quiz_data.get("correct") else 0,
                    quiz_data.get("score", 0),
                    quiz_data.get("max_score", 100),
                    1 if quiz_data.get("passed") else 0,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def get_quiz_records(self, user_id, limit: int = 20) -> list:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, session_id, question, answer, correct, score,
                       max_score, passed, created_at
                FROM quiz_records
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            return [
                {
                    "id": r[0],
                    "session_id": r[1],
                    "question": r[2],
                    "answer": r[3],
                    "correct": bool(r[4]),
                    "score": r[5] or 0,
                    "max_score": r[6] or 100,
                    "passed": bool(r[7]),
                    "created_at": r[8],
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()
