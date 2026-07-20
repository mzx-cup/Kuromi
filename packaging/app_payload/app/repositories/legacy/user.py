"""User repository backed by db.py (MySQL / SQLite / JSON)."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from db import get_db, _is_sqlite, load_local_storage, save_local_storage


def _placeholder(conn) -> str:
    return "?" if _is_sqlite(conn) else "%s"


class DbPyUserRepository:
    def __init__(self, db_path: str = None):
        self.db_path = db_path

    def create_user(self, username: str, password_hash: str, preferred_language: str = "zh-CN") -> int:
        with get_db() as conn:
            if conn is None:
                storage = load_local_storage()
                uid = len(storage.get("users", [])) + 1
                storage.setdefault("users", []).append({
                    "id": uid, "username": username, "password": password_hash,
                    "preferred_language": preferred_language,
                })
                save_local_storage(storage)
                return uid
            cur = conn.cursor()
            ph = _placeholder(conn)
            cur.execute(
                f"INSERT INTO user (username, password, preferred_language) VALUES ({ph}, {ph}, {ph})",
                (username, password_hash, preferred_language),
            )
            conn.commit()
            rid = cur.lastrowid
            cur.close()
            return rid

    def get_by_username(self, username: str) -> dict | None:
        with get_db() as conn:
            if conn is None:
                storage = load_local_storage()
                for u in storage.get("users", []):
                    if u.get("username") == username:
                        return u
                return None
            cur = conn.cursor()
            ph = _placeholder(conn)
            cur.execute(
                f"SELECT * FROM user WHERE username = {ph}",
                (username,),
            )
            row = cur.fetchone()
            if not row:
                cur.close()
                return None
            cols = [d[0] for d in cur.description]
            result = {col: row[i] for i, col in enumerate(cols)}
            cur.close()
            return result

    def record_login(self, user_id, ip: str = "", user_agent: str = "") -> None:
        with get_db() as conn:
            if conn is None:
                return
            cur = conn.cursor()
            ph = _placeholder(conn)
            cur.execute(
                f"INSERT INTO user_login_records (user_id, ip, user_agent, login_at) VALUES ({ph}, {ph}, {ph}, {ph})",
                (user_id, ip, user_agent, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            cur.close()

    def get_login_history(self, user_id) -> list:
        with get_db() as conn:
            if conn is None:
                return []
            cur = conn.cursor()
            ph = _placeholder(conn)
            cur.execute(
                f"SELECT id, ip, user_agent, login_at FROM user_login_records WHERE user_id = {ph} ORDER BY login_at DESC",
                (user_id,),
            )
            result = [{"id": r[0], "ip": r[1], "user_agent": r[2], "login_at": r[3]} for r in cur.fetchall()]
            cur.close()
            return result
