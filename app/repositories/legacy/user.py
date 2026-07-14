"""db.py wrapper for user authentication."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


class DbPyUserRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def create_user(self, username: str, password_hash: str, preferred_language: str = "zh-CN") -> int:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO user (username, password, preferred_language) VALUES (?, ?, ?)",
                (username, password_hash, preferred_language),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def get_by_username(self, username: str) -> dict | None:
        """Look up a user by username; return the full row or None.

        Returns the same shape as ``db.get_user_by_username`` (a dict mapping
        every user-table column) so API layers can access ``role``,
        ``display_name``, ``nickname``, ``avatar`` etc. without reshaping.
        """
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM user WHERE username = ?", (username,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cur.description]
            return {col: row[i] for i, col in enumerate(cols)}
        finally:
            conn.close()

    def record_login(self, user_id, ip: str = "", user_agent: str = "") -> None:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO user_login_records (user_id, ip, user_agent, login_at) VALUES (?, ?, ?, ?)",
                (user_id, ip, user_agent, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_login_history(self, user_id) -> list:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, ip, user_agent, login_at FROM user_login_records WHERE user_id = ? ORDER BY login_at DESC",
                (user_id,),
            )
            return [{"id": r[0], "ip": r[1], "user_agent": r[2], "login_at": r[3]} for r in cur.fetchall()]
        finally:
            conn.close()
