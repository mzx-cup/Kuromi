"""Course progress / learning paths (M5).

归一化方法（course_progress / learning_paths / learning_path_nodes /
user_evaluations / course_deadlines）的**数据家**是 ORM(v2) 管理的库
（默认 xingshi_v2.db，由 ``DATABASE_URL`` 决定）—— 这些表由 ORM
``create_all`` 创建、ORM 写路径写入。旧版本硬连 layer-1 的
storage/xingshi.db（那里根本没有这些表，必报 no such table）。

修复：经 ``orm_conn`` 连数据真正的家，方言占位符 + 日期表达式适配
双引擎；``state`` 列名更正为真实的 ``state_json``；upsert 改为
查-更/插（v2 schema 没有 UNIQUE(user_id, course_id)，ON CONFLICT
子句会直接报错）。

图谱 / 每日路线方法不变 —— 它们本来就委托 db.py 正式函数，跟随
layer-1 生效后端。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from app.repositories.legacy._conn import is_sqlite, orm_conn, ph


class DbPyCourseProgressRepository:
    def __init__(self, db_path: str = None):
        # 测试隔离用（显式 SQLite 文件）；生产为 None → 连 ORM(v2) 库。
        self.db_path = db_path

    # ── course_progress (ORM/v2) ──

    def get_progress(self, user_id, course_id: str) -> Optional[dict]:
        with orm_conn(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT progress_percent, completed_at, last_accessed, state_json
                FROM course_progress
                WHERE user_id = {ph(conn)} AND course_id = {ph(conn)}
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
                "completed_at": str(row[1]) if row[1] is not None else None,
                "last_accessed": str(row[2]) if row[2] is not None else None,
                "state": state,
            }

    def save_progress(
        self,
        user_id,
        course_id: str,
        progress_percent: float,
        state: dict = None,
    ) -> None:
        now_iso = datetime.now().isoformat(sep=" ", timespec="seconds")
        state_json = json.dumps(state or {}, ensure_ascii=False)
        completed_at = now_iso if float(progress_percent) >= 100 else None
        with orm_conn(self.db_path) as conn:
            cur = conn.cursor()
            p = ph(conn)
            cur.execute(
                f"SELECT id FROM course_progress WHERE user_id = {p} AND course_id = {p}",
                (user_id, course_id),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    f"""
                    UPDATE course_progress
                    SET progress_percent = {p}, last_accessed = {p},
                        state_json = {p}, completed_at = COALESCE({p}, completed_at)
                    WHERE id = {p}
                    """,
                    (progress_percent, now_iso, state_json, completed_at, existing[0]),
                )
            else:
                cur.execute(
                    f"""
                    INSERT INTO course_progress
                        (user_id, course_id, progress_percent, completed_at,
                         last_accessed, state_json)
                    VALUES ({p}, {p}, {p}, {p}, {p}, {p})
                    """,
                    (user_id, course_id, progress_percent, completed_at, now_iso, state_json),
                )
            conn.commit()

    # ── learning_paths (ORM/v2) ──

    def get_learning_path(self, user_id) -> list:
        with orm_conn(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT id, name, description, status
                FROM learning_paths
                WHERE user_id = {ph(conn)}
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            paths = []
            for row in cur.fetchall():
                path_id = row[0]
                cur.execute(
                    f"""
                    SELECT id, course_id, title, order_index, completed
                    FROM learning_path_nodes
                    WHERE path_id = {ph(conn)}
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

    # ── user_evaluations (ORM/v2) ──

    def get_evaluations(self, user_id) -> list:
        with orm_conn(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT id, subject, score, max_score, notes, evaluated_at
                FROM user_evaluations
                WHERE user_id = {ph(conn)}
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
                    "evaluated_at": str(r[5]) if r[5] is not None else None,
                }
                for r in cur.fetchall()
            ]

    # ── Upcoming deadlines (slice-11, ORM/v2) ──

    def get_upcoming_deadlines(self, user_id, days: int = 7) -> list:
        """Return course deadlines within the next ``days`` days."""
        with orm_conn(self.db_path) as conn:
            cur = conn.cursor()
            if is_sqlite(conn):
                deadline_expr = "date('now', ?)"
                params = (user_id, f"+{days} days")
            else:
                deadline_expr = "DATE_ADD(CURDATE(), INTERVAL %s DAY)"
                params = (user_id, days)
            cur.execute(
                f"""
                SELECT course_id, title, deadline
                FROM course_deadlines
                WHERE user_id = {ph(conn)} AND deadline <= {deadline_expr}
                ORDER BY deadline ASC LIMIT 20
                """,
                params,
            )
            return [
                {"course_id": row[0], "title": row[1], "deadline": str(row[2])}
                for row in cur.fetchall()
            ]

    # ── Learning-path graph (Task C1) ──
    # The db.py helpers own the per-user graph storage (``learning_path``
    # + ``learning_path_nodes`` tables). Repository methods route through
    # those helpers so the API/service code only ever sees the protocol.

    def get_learning_path_graph(self, user_id) -> dict | None:
        import db as dbmod
        return dbmod.get_learning_path(user_id)

    def save_learning_path_graph(self, user_id, path_json, reasoning=None, data_sources=None, confidence=0.0) -> None:
        import db as dbmod
        dbmod.save_learning_path(
            user_id,
            path_json,
            reasoning=reasoning,
            data_sources=data_sources,
            confidence=confidence,
        )

    def get_learning_path_nodes(self, user_id) -> list:
        import db as dbmod
        return dbmod.get_learning_path_nodes(user_id)

    def get_learning_path_node(self, user_id, node_id) -> dict | None:
        import db as dbmod
        return dbmod.get_learning_path_node(user_id, node_id)

    def save_learning_path_node(self, user_id, node_data: dict) -> bool:
        import db as dbmod
        return bool(dbmod.save_learning_path_node(user_id, node_data))

    def sync_path_to_nodes(self, user_id, path_json) -> int:
        import db as dbmod
        return dbmod.sync_path_to_nodes(user_id, path_json)

    # ── Daily route (Task C1) ──

    def get_daily_route(self, user_id, route_date: str) -> dict | None:
        import db as dbmod
        return dbmod.get_daily_route(user_id, route_date)

    def save_daily_route(self, user_id, route_date: str, tasks, completed=None) -> None:
        import db as dbmod
        dbmod.save_daily_route(user_id, route_date, tasks, completed=completed)
