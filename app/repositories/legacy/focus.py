"""db.py wrapper for focus session tracking (M7).

Provides read/write methods against the db.py tables
``focus_sessions``, ``focus_events`` and ``user_focus_history`` while
M7 gradually shifts the read path to SQLAlchemy.

Only storage operations are exposed here; the flow score formula lives
in higher-level services (see ``app/services/dashboard_data.py``).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, date

import db as _db


def _default_db_path() -> str:
    """Resolve the SQLite path absolutely so the legacy repo doesn't
    accidentally open an empty ``xingshi.db`` next to whatever CWD the
    process happens to be launched from.
    """
    return _db.SQLITE_PATH


class DbPyFocusRepository:
    def __init__(self, db_path: str = None):
        # Default to the absolute path declared in ``db.py``; the relative
        # ``"xingshi.db"`` fallback previously broke legacy reads when the
        # server was launched from the project parent (parent dir has an
        # empty file of the same name).
        self.db_path = db_path or _default_db_path()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    # ── user_focus_history ──

    def get_history(self, user_id: str, days: int = 7) -> list:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT focus_date, total_focus_minutes, sessions_count,
                       avg_flow_score, deep_focus_minutes
                FROM user_focus_history
                WHERE user_id = ? AND focus_date >= date('now', ?)
                ORDER BY focus_date DESC
                """,
                (user_id, f"-{days} days"),
            )
            return [
                {
                    "date": r[0],
                    "total_minutes": r[1] or 0,
                    "sessions": r[2] or 0,
                    "avg_flow_score": r[3] or 0,
                    "deep_focus_minutes": r[4] or 0,
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

    # ── focus_sessions ──

    def start_session(self, user_id: str, planned_minutes: int, subject: str = "") -> int:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO focus_sessions
                (user_id, started_at, planned_minutes, subject)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, datetime.now().isoformat(), planned_minutes, subject),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def end_session(self, session_id: int, duration_minutes: int, completed: bool) -> None:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE focus_sessions
                SET ended_at = ?, duration_minutes = ?, completed = ?
                WHERE id = ?
                """,
                (
                    datetime.now().isoformat(),
                    duration_minutes,
                    1 if completed else 0,
                    session_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    # ── focus_events ──

    def record_event(
        self,
        session_id: int,
        event_type: str,
        flow_score: float,
        metadata: dict = None,
    ) -> None:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT user_id FROM focus_sessions WHERE id = ?",
                (session_id,),
            )
            row = cur.fetchone()
            user_id = row[0] if row else None
            cur.execute(
                """
                INSERT INTO focus_events
                (session_id, user_id, event_type, timestamp, flow_score, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    user_id,
                    event_type,
                    datetime.now().isoformat(),
                    flow_score,
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_events(self, session_id: int) -> list:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, event_type, timestamp, flow_score, metadata_json
                FROM focus_events
                WHERE session_id = ? AND deleted_at IS NULL
                ORDER BY timestamp
                """,
                (session_id,),
            )
            return [
                {
                    "id": r[0],
                    "event_type": r[1],
                    "timestamp": r[2],
                    "flow_score": r[3] or 0,
                    "metadata": r[4],
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()