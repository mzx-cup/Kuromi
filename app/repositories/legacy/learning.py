"""db.py wrapper for learning statistics (read methods M3 + write M4).

存储统一跟随 layer-1 生效后端：读方法对 study_sessions / learning_goals
直连（真实 schema 在两引擎上一致），评价/画像类方法委托 db.py 正式函数。
**不再**各自 ``sqlite3.connect(SQLITE_PATH)`` —— 那会在生效后端为 MySQL
时读错引擎（split-brain 根因之一）。
"""
from __future__ import annotations

import datetime
import json

import db
from app.repositories.legacy._conn import is_sqlite, legacy_conn, legacy_scope, ph


def _as_date_str(value) -> str | None:
    """session_date 兼容转换：SQLite 存 TEXT，MySQL 返回 date/datetime。"""
    if value is None:
        return None
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return str(value)


class DbPyLearningRepository:
    def __init__(self, db_path: str = None):
        # 测试隔离用（显式 SQLite 文件）；生产为 None → 跟随生效后端。
        self.db_path = db_path

    # ── Read methods ──

    def get_overview(self, user_id) -> dict:
        """Return summary stats for the user."""
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            p = ph(conn)
            # Total minutes
            cur.execute(
                f"SELECT COALESCE(SUM(duration_minutes), 0) FROM study_sessions WHERE user_id = {p}",
                (user_id,),
            )
            total_min = cur.fetchone()[0] or 0
            # Distinct study days
            cur.execute(
                f"SELECT COUNT(DISTINCT session_date) FROM study_sessions WHERE user_id = {p}",
                (user_id,),
            )
            study_days = cur.fetchone()[0] or 0
            # Streak (last consecutive days)
            cur.execute(
                f"SELECT DISTINCT session_date FROM study_sessions WHERE user_id = {p} "
                f"ORDER BY session_date DESC LIMIT 30",
                (user_id,),
            )
            dates = [_as_date_str(row[0]) for row in cur.fetchall()]
            streak = 0
            today = datetime.datetime.now().date()
            for i, d in enumerate(dates):
                try:
                    session_d = datetime.date.fromisoformat(str(d)[:10])
                    expected = today - datetime.timedelta(days=i)
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

    def get_trend(self, user_id, days: int) -> list:
        """Return list of {date, minutes} for the last N days."""
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            p = ph(conn)
            if is_sqlite(conn):
                date_expr = "date('now', ?)"
                params = (user_id, f"-{days} days")
            else:
                date_expr = "DATE_SUB(CURDATE(), INTERVAL %s DAY)"
                params = (user_id, days)
            cur.execute(f"""
                SELECT session_date, SUM(duration_minutes)
                FROM study_sessions
                WHERE user_id = {p} AND session_date >= {date_expr}
                GROUP BY session_date
                ORDER BY session_date
            """, params)
            return [
                {"date": _as_date_str(row[0]), "minutes": int(row[1] or 0)}
                for row in cur.fetchall()
            ]

    def get_heatmap(self, user_id) -> dict:
        """Return {date_str: minutes} for the last 365 days."""
        from app.repositories.legacy._conn import date_days_ago
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(f"""
                SELECT session_date, SUM(duration_minutes)
                FROM study_sessions
                WHERE user_id = {ph(conn)} AND session_date >= {date_days_ago(conn, 365)}
                GROUP BY session_date
            """, (user_id,))
            return {
                _as_date_str(row[0]): int(row[1] or 0)
                for row in cur.fetchall()
            }

    def get_mastery(self, user_id) -> list:
        """Return list of {subject, topic, mastery}.

        历史版本查询 ``learning_records(activity_type, minutes)`` —— 该列
        组合在两个引擎的真实库中都不存在（``learning_records`` 实为学习
        画像表，见 db.save_learning_record）。改为从 study_sessions 聚合：
        每科目累计分钟数 → mastery 0-100（10 小时封顶）。
        """
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(f"""
                SELECT subject, SUM(duration_minutes)
                FROM study_sessions
                WHERE user_id = {ph(conn)}
                GROUP BY subject
            """, (user_id,))
            return [
                {
                    "subject": row[0] or "综合",
                    "topic": "累计学习",
                    "mastery": min(100, int(row[1] or 0) // 6),
                }
                for row in cur.fetchall()
            ]

    # ── Write methods (M4) ──

    def record_session(self, user_id, session_data: dict) -> None:
        """Insert a study session record (legacy db.py).

        真实 schema：study_sessions(user_id, session_date, duration_minutes,
        start_time, end_time, subject, node_id)。start_time/end_time /
        node_id 全量提供，避免 MySQL 严格模式下的 NOT NULL 失败。
        旧版本还顺带写 learning_records(activity_type, minutes, metadata)
        —— 那些列在真实库中不存在，写入必然失败，已移除。
        """
        now = datetime.datetime.now()
        minutes = int(
            session_data.get("minutes")
            or session_data.get("duration_minutes")
            or 0
        )
        subject = session_data.get("subject", "")
        session_date = (
            session_data.get("session_date")
            or now.date().isoformat()
        )
        now_iso = now.isoformat(timespec="seconds")
        start_time = session_data.get("start_time") or now_iso
        end_time = session_data.get("end_time") or now_iso

        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                INSERT INTO study_sessions
                (user_id, subject, duration_minutes, session_date,
                 start_time, end_time, node_id, created_at)
                VALUES ({ph(conn)}, {ph(conn)}, {ph(conn)}, {ph(conn)},
                        {ph(conn)}, {ph(conn)}, {ph(conn)}, {ph(conn)})
                """,
                (
                    user_id,
                    subject,
                    minutes,
                    session_date,
                    start_time,
                    end_time,
                    session_data.get("node_id", ""),
                    now_iso,
                ),
            )
            conn.commit()

    def record_goal(self, user_id, goal_data: dict) -> int:
        """Create or update a learning goal. Returns the goal id.

        真实 learning_goals 列（与 db.save_learning_goal 一致）：
        goal_type / title / target_value / current_value / unit /
        start_date / end_date / is_active —— 没有 deadline 列（旧
        想象 schema 才有）；``deadline`` 入参映射到 ``end_date``。
        """
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            p = ph(conn)

            if goal_data.get("id"):
                cur.execute(
                    f"""
                    UPDATE learning_goals
                    SET title = {p}, target_value = {p}, current_value = {p},
                        unit = {p}, end_date = {p}
                    WHERE id = {p} AND user_id = {p}
                    """,
                    (
                        goal_data.get("title", ""),
                        goal_data.get("target_value", 0),
                        goal_data.get("current_value", 0),
                        goal_data.get("unit", "minutes"),
                        goal_data.get("deadline") or goal_data.get("end_date"),
                        goal_data["id"],
                        user_id,
                    ),
                )
                conn.commit()
                return goal_data["id"]

            cur.execute(
                f"""
                INSERT INTO learning_goals
                (user_id, goal_type, title, target_value, current_value,
                 unit, start_date, end_date, is_active)
                VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, 1)
                """,
                (
                    user_id,
                    goal_data.get("goal_type", "daily"),
                    goal_data.get("title", ""),
                    goal_data.get("target_value", 0),
                    goal_data.get("current_value", 0),
                    goal_data.get("unit", "minutes"),
                    goal_data.get("start_date", ""),
                    goal_data.get("deadline") or goal_data.get("end_date") or "",
                ),
            )
            conn.commit()
            return cur.lastrowid

    def delete_goal(self, user_id, goal_id: int) -> None:
        """Delete a learning goal owned by the user."""
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                f"DELETE FROM learning_goals WHERE id = {ph(conn)} AND user_id = {ph(conn)}",
                (goal_id, user_id),
            )
            conn.commit()

    # ── Learning profile + evaluation (A3) ──

    def save_learning_record(self, user_id, record: dict) -> int:
        """Upsert the user's learning-profile snapshot via db.py."""
        profile_json = record.get("profile_json", "{}")
        if not isinstance(profile_json, str):
            profile_json = json.dumps(profile_json, ensure_ascii=False)
        with legacy_scope(self.db_path):
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
        with legacy_scope(self.db_path):
            return db.get_learning_record(user_id)

    def save_user_evaluation(self, user_id, evaluation: dict) -> int:
        """Upsert today's evaluation metrics via db.py. Returns 1 on success."""
        with legacy_scope(self.db_path):
            ok = db.save_user_evaluation(user_id, evaluation)
        return 1 if ok else 0

    def get_user_evaluation(self, user_id, record_date: str | None = None) -> dict | None:
        """Return a single day's evaluation (defaults to today), or None."""
        with legacy_scope(self.db_path):
            return db.get_user_evaluation(user_id, record_date)

    def get_user_evaluation_history(self, user_id, days: int = 7) -> list:
        """Return the most-recent N days of evaluation metrics."""
        with legacy_scope(self.db_path):
            return db.get_user_evaluation_history(user_id, days)
