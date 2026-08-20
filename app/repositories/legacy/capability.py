"""db.py wrapper for capability profile.

聚合 6 个能力维度，全部取自**真实** layer-1 schema：
  - knowledge_base: study_sessions（subject → minutes，schema 真实）
  - code_skill: learning_records.code_practice_time（画像表真实列）
  - cognitive_style: learning_records.profile_json（画像表真实列）
  - focus_level: study_sessions（avg duration + streak，schema 真实）
  - learning_goals: learning_goals（真实表）
  - weakness: study_sessions AVG(duration_minutes) by subject

旧版本的 code_skill / cognitive_style / weakness 查询的是
``learning_records(activity_type, minutes, metadata)`` —— 这些列只存在于
测试 fixture 的想象 schema，两个真实引擎都没有（learning_records 实为
学习画像表）。修复后画像维度改用画像表真实列。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

import db
from app.repositories.legacy._conn import legacy_conn, legacy_scope, ph


def _as_date(raw) -> date | None:
    """session_date 兼容：SQLite TEXT / MySQL date 对象 → date。"""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    try:
        return datetime.fromisoformat(str(raw)).date()
    except (ValueError, TypeError):
        return None


def _streak_from_dates(rows) -> int:
    """从 DESC 排列的 session_date 行计算连续打卡天数。"""
    streak = 0
    today = date.today()
    for i, row in enumerate(rows):
        sd = _as_date(row[0])
        if sd is None:
            break
        if sd == today - timedelta(days=i):
            streak += 1
        else:
            break
    return streak


class DbPyCapabilityRepository:
    def __init__(self, db_path: str = None):
        # 测试隔离用（显式 SQLite 文件）；生产为 None → 跟随生效后端。
        self.db_path = db_path

    async def get_knowledge_base(self, user_id: str) -> dict:
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT subject, SUM(duration_minutes) AS total
                FROM study_sessions
                WHERE user_id = {ph(conn)}
                GROUP BY subject
                """,
                (user_id,),
            )
            rows = cur.fetchall()
            return {subject: min(1.0, total / 600.0) for subject, total in rows if subject}

    async def get_code_skill(self, user_id: str) -> dict:
        """代码能力：画像表 code_practice_time → 0-1（300 分钟封顶）。"""
        with legacy_scope(self.db_path):
            record = db.get_learning_record(user_id)
        minutes = 0
        if record:
            try:
                minutes = int(record.get("code_practice_time") or 0)
            except (TypeError, ValueError):
                minutes = 0
        return {"code": min(1.0, minutes / 300.0)}

    async def get_cognitive_style(self, user_id: str) -> dict:
        """认知风格：画像表 profile_json 里的 modality/depth。"""
        preferred, depth = "visual", "deep"
        with legacy_scope(self.db_path):
            record = db.get_learning_record(user_id)
        if record:
            try:
                profile = json.loads(record.get("profile_json") or "{}")
            except (json.JSONDecodeError, TypeError):
                profile = {}
            if isinstance(profile, dict):
                modality = profile.get("modality") or profile.get("preferred_modality")
                if isinstance(modality, str) and modality:
                    preferred = modality
                if isinstance(profile.get("depth"), str) and profile["depth"]:
                    depth = profile["depth"]
        return {"preferred_modality": preferred, "depth": depth}

    async def get_focus_level(self, user_id: str) -> dict:
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            p = ph(conn)
            cur.execute(
                f"SELECT AVG(duration_minutes) FROM study_sessions WHERE user_id = {p}",
                (user_id,),
            )
            avg = cur.fetchone()[0] or 0
            cur.execute(
                f"""
                SELECT DISTINCT session_date FROM study_sessions
                WHERE user_id = {p} ORDER BY session_date DESC LIMIT 30
                """,
                (user_id,),
            )
            streak = _streak_from_dates(cur.fetchall())
            return {"avg_session_minutes": int(avg), "streak_days": streak}

    async def get_learning_goals(self, user_id: str) -> list:
        """真实 learning_goals 没有 deadline 列，用 end_date 承担该语义。"""
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT id, title, target_value, current_value, unit, end_date
                FROM learning_goals
                WHERE user_id = {ph(conn)}
                  AND is_active = 1
                  AND end_date IS NOT NULL AND end_date != ''
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
                    "deadline": str(row[5]) if row[5] is not None else None,
                })
            return goals

    async def get_weakness(self, user_id: str) -> list:
        """薄弱科目：study_sessions 按科目 AVG(时长)， mastery < 0.4 视为薄弱。"""
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT subject, AVG(duration_minutes) FROM study_sessions
                WHERE user_id = {ph(conn)} GROUP BY subject
                """,
                (user_id,),
            )
            weakness = []
            for subject, avg in cur.fetchall():
                mastery = min(1.0, (avg or 0) / 60.0)
                if mastery < 0.4:
                    weakness.append({"subject": subject, "mastery": mastery})
            return weakness

    async def aggregate_profile(self, user_id: str) -> dict:
        return {
            "knowledge_base": await self.get_knowledge_base(user_id),
            "code_skill": await self.get_code_skill(user_id),
            "cognitive_style": await self.get_cognitive_style(user_id),
            "focus_level": await self.get_focus_level(user_id),
            "learning_goals": await self.get_learning_goals(user_id),
            "weakness": await self.get_weakness(user_id),
        }
