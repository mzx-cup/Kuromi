"""db.py wrapper for focus session tracking (M7).

读写 ``focus_sessions`` / ``focus_events`` / ``user_focus_history``，
跟随 layer-1 生效后端。引擎 schema 差异（均已实测）：

- SQLite (db.py schema)：``user_focus_history`` 带归一化列
  (focus_date, total_focus_minutes, ...)，且存在 focus_sessions /
  focus_events 表。
- MySQL (live)：``user_focus_history`` 只有 focus_json blob；没有
  focus_sessions / focus_events 表。

因此 ``get_history`` 按方言分流：SQLite 读归一化列，MySQL 读
focus_json blob 再映射。会话/事件方法依赖的 focus_sessions 表是
db.py schema 的一部分，MySQL 库缺表时显式报错（不静默换库）。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from app.repositories.legacy._conn import is_sqlite, legacy_conn, ph


def _focus_history_from_blob(blob: str | None) -> list:
    """MySQL 分支：focus_json blob → get_history 契约形状。

    blob 结构由 db.save_user_focus_history 写入，常见形状
    ``{"history": [{date, total_minutes, ...}]}`` 或直接是列表；
    做防御性映射，缺字段补 0。
    """
    if not blob:
        return []
    try:
        data = json.loads(blob)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(data, dict):
        data = data.get("history") or data.get("records") or []
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        out.append({
            "date": item.get("date") or item.get("focus_date"),
            "total_minutes": item.get("total_minutes", 0),
            "sessions": item.get("sessions", item.get("sessions_count", 0)),
            "avg_flow_score": item.get("avg_flow_score", 0),
            "deep_focus_minutes": item.get("deep_focus_minutes", 0),
        })
    return out


class DbPyFocusRepository:
    def __init__(self, db_path: str = None):
        # 测试隔离用（显式 SQLite 文件）；生产为 None → 跟随生效后端。
        self.db_path = db_path

    def _require_focus_tables(self, conn) -> None:
        """MySQL 缺 focus_sessions/focus_events 表时显式报错。

        SQLite 的这两张表由 db.py schema 建（每次初始化都会建）；
        live MySQL 从未建过它们 —— 以前这里会静默写进 SQLite 造成
        跨引擎分裂，现在改为直接抛错提示补建。
        """
        if is_sqlite(conn):
            return
        cur = conn.cursor()
        cur.execute("SHOW TABLES LIKE 'focus_sessions'")
        if not cur.fetchone():
            raise RuntimeError(
                "focus_sessions/focus_events tables do not exist on the "
                "effective MySQL backend. Run Navicat/setup_database.py "
                "(focus_sessions DDL) or switch STARLEARN_DB_BACKEND=sqlite."
            )

    # ── user_focus_history ──

    def get_history(self, user_id: str, days: int = 7) -> list:
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            if is_sqlite(conn):
                cur.execute(
                    """
                    SELECT focus_date, total_focus_minutes, sessions_count,
                           avg_flow_score, deep_focus_minutes
                    FROM user_focus_history
                    WHERE user_id = ? AND focus_date >= date('now', ?)
                      AND deleted_at IS NULL
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
            # MySQL：只有 focus_json blob
            cur.execute(
                "SELECT focus_json FROM user_focus_history WHERE user_id = %s "
                "ORDER BY updated_at DESC LIMIT 1",
                (user_id,),
            )
            row = cur.fetchone()
            blob = row[0] if row else None
            history = _focus_history_from_blob(blob)
            history.sort(key=lambda h: h["date"] or "", reverse=True)
            return history[:days]

    # ── focus_sessions ──

    def start_session(self, user_id: str, planned_minutes: int, subject: str = "") -> int:
        with legacy_conn(self.db_path) as conn:
            self._require_focus_tables(conn)
            cur = conn.cursor()
            cur.execute(
                f"""
                INSERT INTO focus_sessions
                (user_id, started_at, planned_minutes, subject)
                VALUES ({ph(conn)}, {ph(conn)}, {ph(conn)}, {ph(conn)})
                """,
                (user_id, datetime.now().isoformat(), planned_minutes, subject),
            )
            conn.commit()
            return cur.lastrowid

    def end_session(self, session_id: int, duration_minutes: int, completed: bool) -> None:
        with legacy_conn(self.db_path) as conn:
            self._require_focus_tables(conn)
            cur = conn.cursor()
            cur.execute(
                f"""
                UPDATE focus_sessions
                SET ended_at = {ph(conn)}, duration_minutes = {ph(conn)}, completed = {ph(conn)}
                WHERE id = {ph(conn)}
                """,
                (
                    datetime.now().isoformat(),
                    duration_minutes,
                    1 if completed else 0,
                    session_id,
                ),
            )
            conn.commit()

    # ── focus_events ──

    def record_event(
        self,
        session_id: int,
        event_type: str,
        flow_score: float,
        metadata: dict = None,
    ) -> None:
        with legacy_conn(self.db_path) as conn:
            self._require_focus_tables(conn)
            cur = conn.cursor()
            cur.execute(
                f"SELECT user_id FROM focus_sessions WHERE id = {ph(conn)}",
                (session_id,),
            )
            row = cur.fetchone()
            user_id = row[0] if row else None
            cur.execute(
                f"""
                INSERT INTO focus_events
                (session_id, user_id, event_type, timestamp, flow_score, metadata_json)
                VALUES ({ph(conn)}, {ph(conn)}, {ph(conn)}, {ph(conn)}, {ph(conn)}, {ph(conn)})
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

    def get_events(self, session_id: int) -> list:
        with legacy_conn(self.db_path) as conn:
            self._require_focus_tables(conn)
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT id, event_type, timestamp, flow_score, metadata_json
                FROM focus_events
                WHERE session_id = {ph(conn)} AND deleted_at IS NULL
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
