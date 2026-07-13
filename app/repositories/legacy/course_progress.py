"""db.py wrapper for course progress and learning paths (M5).

Provides read/write methods against the db.py tables
``course_progress``, ``learning_paths``, ``learning_path_nodes``
and ``user_evaluations`` while M5 gradually shifts the read
path to SQLAlchemy.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Optional


class DbPyCourseProgressRepository:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or "xingshi.db"

    def _conn(self):
        return sqlite3.connect(self.db_path)

    # ── course_progress ──

    def get_progress(self, user_id, course_id: str) -> Optional[dict]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT progress_percent, completed_at, last_accessed, state
                FROM course_progress
                WHERE user_id = ? AND course_id = ?
                """,
                (user_id, course_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            try:
                state = json.loads(row[3]) if row[3] else {}
            except (json.JSONDecodeError, TypeError):
                state = {}
            return {
                "progress_percent": row[0] or 0,
                "completed_at": row[1],
                "last_accessed": row[2],
                "state": state,
            }
        finally:
            conn.close()

    def save_progress(
        self,
        user_id,
        course_id: str,
        progress_percent: float,
        state: dict = None,
    ) -> None:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO course_progress
                    (user_id, course_id, progress_percent, last_accessed, state)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, course_id) DO UPDATE SET
                    progress_percent = excluded.progress_percent,
                    last_accessed = excluded.last_accessed,
                    state = excluded.state
                """,
                (
                    user_id,
                    course_id,
                    progress_percent,
                    datetime.now().isoformat(),
                    json.dumps(state or {}, ensure_ascii=False),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    # ── learning_paths ──

    def get_learning_path(self, user_id) -> list:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, description, status
                FROM learning_paths
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            paths = []
            for row in cur.fetchall():
                path_id = row[0]
                cur.execute(
                    """
                    SELECT id, course_id, title, order_index, completed
                    FROM learning_path_nodes
                    WHERE path_id = ?
                    ORDER BY order_index
                    """,
                    (path_id,),
                )
                nodes = [
                    {
                        "id": n[0],
                        "course_id": n[1],
                        "title": n[2],
                        "order": n[3],
                        "completed": bool(n[4]),
                    }
                    for n in cur.fetchall()
                ]
                paths.append(
                    {
                        "id": path_id,
                        "name": row[1],
                        "description": row[2],
                        "status": row[3],
                        "nodes": nodes,
                    }
                )
            return paths
        finally:
            conn.close()

    # ── user_evaluations ──

    def get_evaluations(self, user_id) -> list:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, subject, score, max_score, notes, evaluated_at
                FROM user_evaluations
                WHERE user_id = ?
                ORDER BY evaluated_at DESC
                """,
                (user_id,),
            )
            return [
                {
                    "id": r[0],
                    "subject": r[1],
                    "score": r[2],
                    "max_score": r[3],
                    "notes": r[4],
                    "evaluated_at": r[5],
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

    # ── Upcoming deadlines (slice-11) ──

    def get_upcoming_deadlines(self, user_id, days: int = 7) -> list:
        """Return course deadlines within the next ``days`` days."""
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT course_id, title, deadline
                FROM course_deadlines
                WHERE user_id = ? AND deadline <= date('now', ?)
                ORDER BY deadline ASC LIMIT 20
            """, (user_id, f"+{days} days"))
            return [
                {"course_id": row[0], "title": row[1], "deadline": row[2]}
                for row in cur.fetchall()
            ]
        finally:
            conn.close()
