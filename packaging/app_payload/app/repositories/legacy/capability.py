"""db.py wrapper for capability profile.

Aggregates 6 user capability dimensions from db.py tables:
  - knowledge_base: from study_sessions (subject → minutes)
  - code_skill: from learning_records (subject where activity_type='code')
  - cognitive_style: from learning_records.metadata (preferred_modality)
  - focus_level: from study_sessions (avg session duration, streak)
  - learning_goals: from learning_goals table
  - weakness: from learning_records (subjects with low avg minutes)
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional


class DbPyCapabilityRepository:
    def __init__(self, db_path: str = None):
        # Use the absolute path from db.py so legacy reads open the same
        # SQLite file the rest of the project uses (CWD-agnostic).
        import db as _db
        self.db_path = db_path or _db.SQLITE_PATH

    def _conn(self):
        return sqlite3.connect(self.db_path)

    async def get_knowledge_base(self, user_id: str) -> dict:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT subject, SUM(duration_minutes) AS total
                FROM study_sessions
                WHERE user_id = ?
                GROUP BY subject
                """,
                (user_id,),
            )
            rows = cur.fetchall()
            return {subject: min(1.0, total / 600.0) for subject, total in rows if subject}
        finally:
            conn.close()

    async def get_code_skill(self, user_id: str) -> dict:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT subject, SUM(minutes) AS total
                FROM learning_records
                WHERE user_id = ? AND activity_type = 'code'
                GROUP BY subject
                """,
                (user_id,),
            )
            rows = cur.fetchall()
            return {subject: min(1.0, total / 300.0) for subject, total in rows if subject}
        finally:
            conn.close()

    async def get_cognitive_style(self, user_id: str) -> dict:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT metadata FROM learning_records
                WHERE user_id = ? AND metadata IS NOT NULL
                ORDER BY recorded_at DESC LIMIT 20
                """,
                (user_id,),
            )
            modalities = []
            for (meta_str,) in cur.fetchall():
                try:
                    meta = json.loads(meta_str)
                    if "modality" in meta:
                        modalities.append(meta["modality"])
                except (json.JSONDecodeError, TypeError):
                    pass
            preferred = max(set(modalities), key=modalities.count) if modalities else "visual"
            return {"preferred_modality": preferred, "depth": "deep"}
        finally:
            conn.close()

    async def get_focus_level(self, user_id: str) -> dict:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT AVG(duration_minutes) FROM study_sessions WHERE user_id = ?
                """,
                (user_id,),
            )
            avg = cur.fetchone()[0] or 0
            cur.execute(
                """
                SELECT DISTINCT session_date FROM study_sessions
                WHERE user_id = ? ORDER BY session_date DESC LIMIT 30
                """,
                (user_id,),
            )
            dates = [row[0] for row in cur.fetchall()]
            streak = 0
            today = date.today()
            for i, d in enumerate(dates):
                try:
                    sd = datetime.fromisoformat(d).date() if isinstance(d, str) else d
                    if sd == today - timedelta(days=i):
                        streak += 1
                    else:
                        break
                except (ValueError, TypeError):
                    break
            return {"avg_session_minutes": int(avg), "streak_days": streak}
        finally:
            conn.close()

    async def get_learning_goals(self, user_id: str) -> list:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, title, target_value, current_value, unit, deadline
                FROM learning_goals WHERE user_id = ? AND deadline IS NOT NULL
                """,
                (user_id,),
            )
            goals = []
            for row in cur.fetchall():
                target = row[2] or 1
                progress = (row[3] or 0) / target if target else 0
                goals.append({
                    "id": row[0],
                    "title": row[1],
                    "progress": min(1.0, progress),
                    "unit": row[4],
                    "deadline": row[5],
                })
            return goals
        finally:
            conn.close()

    async def get_weakness(self, user_id: str) -> list:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT subject, AVG(minutes) FROM learning_records
                WHERE user_id = ? GROUP BY subject
                """,
                (user_id,),
            )
            weakness = []
            for subject, avg in cur.fetchall():
                mastery = min(1.0, (avg or 0) / 60.0)
                if mastery < 0.4:
                    weakness.append({"subject": subject, "mastery": mastery})
            return weakness
        finally:
            conn.close()

    async def aggregate_profile(self, user_id: str) -> dict:
        return {
            "knowledge_base": await self.get_knowledge_base(user_id),
            "code_skill": await self.get_code_skill(user_id),
            "cognitive_style": await self.get_cognitive_style(user_id),
            "focus_level": await self.get_focus_level(user_id),
            "learning_goals": await self.get_learning_goals(user_id),
            "weakness": await self.get_weakness(user_id),
        }
