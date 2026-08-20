"""db.py wrapper for classroom sessions and quiz records (M10).

真实 schema（两引擎一致）：``classroom_sessions(id TEXT PK, student_id,
course_id, course_data, current_scene_index, status, teacher_persona,
...)``、``quiz_records(classroom_id, student_id, quiz_id, score, total,
passed, answers, feedback)``。

旧版本查询 ``user_id`` / ``started_at`` / ``current_slide`` /
``teacher_mode`` / ``session_id`` / ``question`` 等想象列 —— 真实表全
都没有；且旧版本直连 SQLite，生产 MySQL 生效时读不到。本版本跟随
生效后端 + 真实列名，键名映射到既有调用契约。
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime

import db
from app.repositories.legacy._conn import legacy_conn, legacy_scope, ph

_SESSION_SELECT = """
    SELECT id, student_id, course_id, current_scene_index, status,
           teacher_persona, created_at, updated_at
    FROM classroom_sessions
"""


def _session_row(row) -> dict:
    return {
        "id": row[0],
        "user_id": row[1],
        "course_id": row[2],
        "started_at": row[6],
        "ended_at": row[7],
        "current_slide": row[3] or 0,
        "status": row[4] or "active",
        "teacher_mode": bool(row[5]),
    }


def _quiz_answers_blob(quiz_data: dict) -> str:
    """契约里的 question/answer/correct → 真实表 answers JSON。"""
    answers = quiz_data.get("answers")
    if answers is None:
        answers = [{
            "question": quiz_data.get("question", ""),
            "answer": quiz_data.get("answer", ""),
            "correct": bool(quiz_data.get("correct")),
        }]
    return json.dumps(answers, ensure_ascii=False)


class DbPyClassroomRepository:
    def __init__(self, db_path: str = None):
        # 测试隔离用（显式 SQLite 文件）；生产为 None → 跟随生效后端。
        self.db_path = db_path

    # ── sessions ──

    def get_session(self, session_id) -> dict | None:
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                f"{_SESSION_SELECT} WHERE id = {ph(conn)}",
                (str(session_id),),
            )
            row = cur.fetchone()
            return _session_row(row) if row else None

    def list_sessions(self, user_id) -> list:
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT id, student_id, course_id, current_scene_index, status,
                       teacher_persona, created_at, updated_at
                FROM classroom_sessions
                WHERE student_id = {ph(conn)}
                ORDER BY created_at DESC
                """,
                (str(user_id),),
            )
            return [
                {
                    "id": r[0],
                    "course_id": r[2],
                    "started_at": r[6],
                    "ended_at": r[7],
                    "current_slide": r[3] or 0,
                    "status": r[4] or "active",
                }
                for r in cur.fetchall()
            ]

    def create_session(self, user_id, course_id: str, teacher_mode: bool = False) -> str:
        # 两引擎的 id 都是 TEXT PK（MySQL VARCHAR(64) / SQLite TEXT），生成字符串 id
        session_id = f"cs_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now().isoformat(sep=" ", timespec="seconds")
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            p = ph(conn)
            cur.execute(
                f"""
                INSERT INTO classroom_sessions
                (id, student_id, course_id, course_data, current_scene_index,
                 status, teacher_persona, created_at, updated_at)
                VALUES ({p}, {p}, {p}, {p}, 0, 'active', {p}, {p}, {p})
                """,
                (
                    session_id,
                    str(user_id),
                    course_id,
                    "{}",
                    "expert_mentor" if teacher_mode else "study_buddy",
                    now_iso,
                    now_iso,
                ),
            )
            conn.commit()
            return session_id

    def update_session(self, session_id, updates: dict) -> None:
        # 契约键 → 真实列（current_slide/ended_at/teacher_mode 是想象名）
        key_map = {
            "current_slide": "current_scene_index",
            "status": "status",
            "ended_at": "updated_at",
            "course_id": "course_id",
            "current_scene_index": "current_scene_index",
            "updated_at": "updated_at",
            "teacher_persona": "teacher_persona",
            "teacher_mode": "teacher_persona",
        }
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            sets = []
            values = []
            for k, v in updates.items():
                col = key_map.get(k)
                if col is None:
                    continue
                if k == "teacher_mode":
                    v = "expert_mentor" if v else "study_buddy"
                sets.append(f"{col} = {ph(conn)}")
                values.append(v)
            if not sets:
                return
            sets.append(f"updated_at = {ph(conn)}")
            values.append(datetime.now().isoformat(sep=" ", timespec="seconds"))
            values.append(str(session_id))
            cur.execute(
                f"UPDATE classroom_sessions SET {', '.join(sets)} WHERE id = {ph(conn)}",
                values,
            )
            conn.commit()

    # ── quiz records ──

    def save_quiz_record(self, user_id, quiz_data: dict) -> int:
        now_iso = datetime.now().isoformat(sep=" ", timespec="seconds")
        passed = 1 if quiz_data.get("passed", quiz_data.get("correct")) else 0
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            p = ph(conn)
            cur.execute(
                f"""
                INSERT INTO quiz_records
                (classroom_id, student_id, quiz_id, score, total, passed,
                 answers, feedback, created_at, updated_at)
                VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
                """,
                (
                    str(quiz_data.get("session_id") or quiz_data.get("classroom_id") or ""),
                    str(user_id),
                    str(quiz_data.get("quiz_id", "")),
                    quiz_data.get("score", 0),
                    quiz_data.get("max_score", quiz_data.get("total", 100)),
                    passed,
                    _quiz_answers_blob(quiz_data),
                    json.dumps(quiz_data.get("feedback") or {}, ensure_ascii=False),
                    now_iso,
                    now_iso,
                ),
            )
            conn.commit()
            return cur.lastrowid

    def get_quiz_records(self, user_id, limit: int = 20) -> list:
        with legacy_scope(self.db_path):
            rows = db.get_recent_quizzes(user_id, limit) or []
        out = []
        for i, r in enumerate(rows):
            answers = r.get("answers")
            if isinstance(answers, str):
                try:
                    answers = json.loads(answers)
                except (json.JSONDecodeError, TypeError):
                    answers = []
            first = answers[0] if isinstance(answers, list) and answers else {}
            if not isinstance(first, dict):
                first = {}
            out.append({
                "id": r.get("quiz_id") or i + 1,
                "session_id": r.get("classroom_id", ""),
                "question": first.get("question", ""),
                "answer": first.get("answer", ""),
                "correct": bool(r.get("passed")),
                "score": r.get("score") or 0,
                "max_score": r.get("total") or 100,
                "passed": bool(r.get("passed")),
                "created_at": str(r.get("created_at")) if r.get("created_at") is not None else None,
            })
        return out
