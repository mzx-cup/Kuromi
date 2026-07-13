"""db.py wrapper for learning statistics (read methods only in M3).

Implements read methods for the learning statistics slice. Write methods
are stubs and will be filled in M4.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta

import db


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

    # ── Write methods (M4) ──

    def record_session(self, user_id, session_data: dict) -> None:
        """Insert a study session record (legacy db.py).

        Writes both study_sessions and learning_records rows so the
        overview/trend/mastery read paths remain consistent.
        """
        from datetime import datetime

        conn = self._conn()
        try:
            cur = conn.cursor()
            minutes = int(
                session_data.get("minutes")
                or session_data.get("duration_minutes")
                or 0
            )
            subject = session_data.get("subject", "")
            session_date = (
                session_data.get("session_date")
                or datetime.now().date().isoformat()
            )
            now_iso = datetime.now().isoformat()

            cur.execute(
                """
                INSERT INTO study_sessions
                (user_id, subject, duration_minutes, session_date, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, subject, minutes, session_date, now_iso),
            )
            cur.execute(
                """
                INSERT INTO learning_records
                (user_id, activity_type, subject, minutes, metadata, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    session_data.get("activity_type", "study"),
                    subject,
                    minutes,
                    json.dumps(
                        session_data.get("metadata", {}), ensure_ascii=False
                    ),
                    now_iso,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def record_goal(self, user_id, goal_data: dict) -> int:
        """Create or update a learning goal. Returns the goal id."""
        from datetime import datetime

        conn = self._conn()
        try:
            cur = conn.cursor()
            now_iso = datetime.now().isoformat()

            if goal_data.get("id"):
                cur.execute(
                    """
                    UPDATE learning_goals
                    SET title = ?, target_value = ?, current_value = ?,
                        unit = ?, deadline = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (
                        goal_data.get("title", ""),
                        goal_data.get("target_value", 0),
                        goal_data.get("current_value", 0),
                        goal_data.get("unit", "minutes"),
                        goal_data.get("deadline"),
                        goal_data["id"],
                        user_id,
                    ),
                )
                conn.commit()
                return goal_data["id"]
            else:
                cur.execute(
                    """
                    INSERT INTO learning_goals
                    (user_id, title, target_value, current_value, unit,
                     deadline, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        goal_data.get("title", ""),
                        goal_data.get("target_value", 0),
                        goal_data.get("current_value", 0),
                        goal_data.get("unit", "minutes"),
                        goal_data.get("deadline"),
                        now_iso,
                    ),
                )
                conn.commit()
                return cur.lastrowid
        finally:
            conn.close()

    def delete_goal(self, user_id, goal_id: int) -> None:
        """Delete a learning goal owned by the user."""
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM learning_goals WHERE id = ? AND user_id = ?",
                (goal_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()

    # ── Learning profile + evaluation (A3) ──

    def save_learning_record(self, user_id, record: dict) -> int:
        """Upsert the user's learning-profile snapshot via db.py."""
        profile_json = record.get("profile_json", "{}")
        if not isinstance(profile_json, str):
            profile_json = json.dumps(profile_json, ensure_ascii=False)
        db.save_learning_record(
            user_id,
            record.get("interaction_count", 0),
            record.get("code_practice_time", 0),
            record.get("socratic_pass_rate", 0.0),
            record.get("difficulty_level", "basic"),
            profile_json,
        )
        return 1

    def get_learning_record(self, user_id) -> dict | None:
        """Return the user's learning-profile snapshot, or None."""
        return db.get_learning_record(user_id)

    def save_user_evaluation(self, user_id, evaluation: dict) -> int:
        """Upsert today's evaluation metrics via db.py. Returns 1 on success."""
        ok = db.save_user_evaluation(user_id, evaluation)
        return 1 if ok else 0

    def get_user_evaluation(self, user_id, record_date: str | None = None) -> dict | None:
        """Return a single day's evaluation (defaults to today), or None."""
        return db.get_user_evaluation(user_id, record_date)

    def get_user_evaluation_history(self, user_id, days: int = 7) -> list:
        """Return the most-recent N days of evaluation metrics."""
        return db.get_user_evaluation_history(user_id, days)
