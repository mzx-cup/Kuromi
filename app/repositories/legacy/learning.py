"""db.py wrapper for learning statistics (read methods only in M3).

Implements read methods for the learning statistics slice. Write methods
are stubs and will be filled in M4.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta


class DbPyLearningRepository:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or "xingshi.db"

    def _conn(self):
        return sqlite3.connect(self.db_path)

    # ── Read methods ──

    def get_overview(self, user_id) -> dict:
        """Return summary stats for the user."""
        conn = self._conn()
        try:
            cur = conn.cursor()
            # Total minutes
            cur.execute(
                "SELECT COALESCE(SUM(duration_minutes), 0) FROM study_sessions WHERE user_id = ?",
                (user_id,),
            )
            total_min = cur.fetchone()[0] or 0
            # Distinct study days
            cur.execute(
                "SELECT COUNT(DISTINCT session_date) FROM study_sessions WHERE user_id = ?",
                (user_id,),
            )
            study_days = cur.fetchone()[0] or 0
            # Streak (last consecutive days)
            cur.execute(
                "SELECT DISTINCT session_date FROM study_sessions WHERE user_id = ? ORDER BY session_date DESC LIMIT 30",
                (user_id,),
            )
            dates = [row[0] for row in cur.fetchall()]
            streak = 0
            today = datetime.now().date()
            for i, d in enumerate(dates):
                try:
                    session_d = datetime.fromisoformat(d).date()
                    expected = today - timedelta(days=i)
                    if session_d == expected:
                        streak += 1
                    else:
                        break
                except (ValueError, TypeError):
                    break
            return {
                "total_minutes": int(total_min),
                "study_days": int(study_days),
                "current_streak": streak,
            }
        finally:
            conn.close()

    def get_trend(self, user_id, days: int) -> list:
        """Return list of {date, minutes} for the last N days."""
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT session_date, SUM(duration_minutes)
                FROM study_sessions
                WHERE user_id = ? AND session_date >= date('now', ?)
                GROUP BY session_date
                ORDER BY session_date
            """, (user_id, f"-{days} days"))
            return [{"date": row[0], "minutes": int(row[1] or 0)} for row in cur.fetchall()]
        finally:
            conn.close()

    def get_heatmap(self, user_id) -> dict:
        """Return {date_str: minutes} for the last 365 days."""
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT session_date, SUM(duration_minutes)
                FROM study_sessions
                WHERE user_id = ? AND session_date >= date('now', '-365 days')
                GROUP BY session_date
            """, (user_id,))
            return {row[0]: int(row[1] or 0) for row in cur.fetchall()}
        finally:
            conn.close()

    def get_mastery(self, user_id) -> list:
        """Return list of {subject, topic, mastery}."""
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT subject, activity_type, AVG(minutes)
                FROM learning_records
                WHERE user_id = ?
                GROUP BY subject, activity_type
            """, (user_id,))
            return [
                {"subject": row[0], "topic": row[1], "mastery": min(100, int(row[2] or 0) * 2)}
                for row in cur.fetchall()
            ]
        finally:
            conn.close()

    # ── Write stub (M4's responsibility) ──

    def record_session(self, user_id, session_data: dict) -> None:
        raise NotImplementedError("Write path is M4's responsibility")
