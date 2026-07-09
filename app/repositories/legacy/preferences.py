"""db.py wrapper for user preferences, settings, and theme sync."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone


class DbPyPreferencesRepository:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or "xingshi.db"

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def get_preferences(self, user_id: str) -> dict:
        """Return {key: value} dict for the user."""
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT key, value FROM user_preferences WHERE user_id = ?",
                (user_id,),
            )
            result = {}
            for row in cur.fetchall():
                try:
                    result[row[0]] = json.loads(row[1]) if row[1] else {}
                except (json.JSONDecodeError, TypeError):
                    result[row[0]] = row[1]
            return result
        finally:
            conn.close()

    def set_preference(self, user_id: str, key: str, value: dict) -> None:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO user_preferences (user_id, key, value, updated_at) VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """, (user_id, key, json.dumps(value, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))
            conn.commit()
        finally:
            conn.close()

    def get_settings(self, user_id: str) -> dict:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT setting_key, setting_value FROM user_settings WHERE user_id = ?",
                (user_id,),
            )
            return {row[0]: row[1] for row in cur.fetchall()}
        finally:
            conn.close()

    def set_setting(self, user_id: str, key: str, value: str) -> None:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO user_settings (user_id, setting_key, setting_value, updated_at) VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, setting_key) DO UPDATE SET setting_value = excluded.setting_value, updated_at = excluded.updated_at
            """, (user_id, key, value, datetime.now(timezone.utc).isoformat()))
            conn.commit()
        finally:
            conn.close()

    def get_theme(self, user_id: str) -> dict:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT theme, accent_color FROM user_themes WHERE user_id = ?",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return {"theme": "dark", "accent_color": "#7c3aed"}
            return {"theme": row[0], "accent_color": row[1]}
        finally:
            conn.close()

    def set_theme(self, user_id: str, theme: str, accent_color: str = "#7c3aed") -> None:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO user_themes (user_id, theme, accent_color, updated_at) VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET theme = excluded.theme, accent_color = excluded.accent_color, updated_at = excluded.updated_at
            """, (user_id, theme, accent_color, datetime.now(timezone.utc).isoformat()))
            conn.commit()
        finally:
            conn.close()
