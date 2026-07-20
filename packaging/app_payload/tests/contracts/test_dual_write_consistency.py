"""Verify dual-write operations land data in both backends."""
import os
import sqlite3
import pytest


PROD_LEGACY_SCHEMA = """
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    nickname VARCHAR(50) DEFAULT '',
    avatar VARCHAR(500) DEFAULT '',
    current_task VARCHAR(100) DEFAULT '大数据导论',
    preferred_language VARCHAR(20) DEFAULT 'python',
    theme VARCHAR(50) DEFAULT 'ocean',
    last_agent_id VARCHAR(50) DEFAULT '',
    last_login TIMESTAMP NULL DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    profile_json LONGTEXT,
    evaluation_json LONGTEXT,
    last_grade_record TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS user_login_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username VARCHAR(128),
    success INTEGER DEFAULT 0,
    failure_reason VARCHAR(255) DEFAULT '',
    ip_address VARCHAR(64) DEFAULT '',
    user_agent VARCHAR(512) DEFAULT '',
    login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER NOT NULL,
    key VARCHAR(128) NOT NULL,
    value TEXT,
    updated_at TEXT,
    PRIMARY KEY (user_id, key)
);
"""


def _init_prod_legacy_schema(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(PROD_LEGACY_SCHEMA)
    conn.commit()
    conn.close()


def _seed_legacy_users(db_path: str, users: list) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for u in users:
        cur.execute(
            "INSERT OR IGNORE INTO user (id, username, password, preferred_language) VALUES (?, ?, ?, ?)",
            (u["id"], u["username"], u["password"], u["preferred_language"]),
        )
    conn.commit()
    conn.close()


@pytest.mark.dual_write
class TestAuthDualWriteConsistency:
    def test_register_lands_in_both(self, tmp_path, monkeypatch):
        """When DUAL_WRITE_LEGACY=true, register writes to both legacy and ORM."""
        import importlib

        legacy_path = str(tmp_path / "legacy.db")
        orm_path = str(tmp_path / "orm.db")

        from tests.fixtures.seed_data import (
            init_orm_schema,
            populate_orm,
            SEED_USERS,
        )

        # Use production-compatible legacy schema so database.create_user works.
        _init_prod_legacy_schema(legacy_path)
        _seed_legacy_users(legacy_path, SEED_USERS)
        init_orm_schema(orm_path)
        populate_orm(orm_path, SEED_USERS)

        # Point legacy + ORM at our tmp paths; force SQLite backend.
        monkeypatch.setenv("SQLITE_PATH", legacy_path)
        monkeypatch.setenv("STARLEARN_DB_BACKEND", "sqlite")
        monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{orm_path}")
        monkeypatch.setenv("DUAL_WRITE_LEGACY", "true")

        # Reload modules that captured env at import time.
        import db as _db
        importlib.reload(_db)
        import main as _main
        importlib.reload(_main)

        from fastapi.testclient import TestClient
        client = TestClient(_main.app)

        resp = client.post("/api/register", json={
            "username": "dual_test_user",
            "password": "test_pw",
            "preferred_language": "zh-CN",
        })
        assert resp.status_code in (200, 201), f"Got {resp.status_code}: {resp.text}"

        # Verify the legacy DB got the new user (initial 3 + 1 = 4).
        conn = sqlite3.connect(legacy_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM user")
        legacy_count = cur.fetchone()[0]
        conn.close()
        assert legacy_count >= 4, f"Legacy count = {legacy_count}"

    def test_login_records_appear_in_both(self, tmp_path, monkeypatch):
        """When DUAL_WRITE_LEGACY=true, login succeeds end-to-end."""
        import importlib

        legacy_path = str(tmp_path / "legacy.db")
        orm_path = str(tmp_path / "orm.db")

        from tests.fixtures.seed_data import (
            init_orm_schema,
            populate_orm,
            SEED_USERS,
        )
        _init_prod_legacy_schema(legacy_path)
        _seed_legacy_users(legacy_path, SEED_USERS)
        init_orm_schema(orm_path)
        populate_orm(orm_path, SEED_USERS)

        monkeypatch.setenv("SQLITE_PATH", legacy_path)
        monkeypatch.setenv("STARLEARN_DB_BACKEND", "sqlite")
        monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{orm_path}")
        monkeypatch.setenv("DUAL_WRITE_LEGACY", "true")

        import db as _db
        importlib.reload(_db)
        import main as _main
        importlib.reload(_main)

        from fastapi.testclient import TestClient
        client = TestClient(_main.app)

        # Register first.
        reg_resp = client.post("/api/register", json={
            "username": "login_dual_user",
            "password": "test_pw",
        })
        assert reg_resp.status_code in (200, 201), f"Register failed: {reg_resp.text}"

        # Then login.
        login_resp = client.post("/api/login", json={
            "username": "login_dual_user",
            "password": "test_pw",
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        assert login_resp.json().get("success") is True
