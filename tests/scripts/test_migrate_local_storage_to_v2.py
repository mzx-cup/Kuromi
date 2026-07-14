"""One-shot migration: local_storage.json → xingshi_v2.db (Phase 2.1).

The 5 collections in local_storage.json map to ORM tables:

| JSON collection          | ORM target table           | Notable transforms                            |
|--------------------------|----------------------------|-----------------------------------------------|
| users                    | users                      | id int→str; password→password_hash;           |
|                          |                            | avatar→avatar_url; display_name→nickname      |
| user_login_records       | user_login_records         | adds username/success/failure_reason/         |
|                          |                            | created_at via ALTER TABLE                    |
| classroom_records        | classroom_sessions         | id int→str; course_data gets full_data JSON   |
|                          |                            | (no UNIQUE(course_id) — one course per user)  |
| daily_routes             | daily_routes               | tasks→tasks_json; date→route_date             |
| user_flashcard_progress  | user_flashcard_progress    | new table; front→front_text, back→back_text, |
|                          |                            | hint→hint_text                                |

Strategy: read JSON → open v2.db → run idempotent migrations (CREATE TABLE IF NOT
EXISTS, ALTER TABLE add column if missing) → INSERT OR IGNORE/REPLACE each row.
The script is safe to re-run; it never deletes existing rows.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts import migrate_local_storage_to_v2 as mig


def _ensure_v2_db_schema(target_db: Path) -> None:
    """Recreate the 4 ORM-managed tables + 1 db.py-style flashcard table in
    the test database. Mirrors the production v2.db schema, which the
    migration assumes already exists."""
    conn = sqlite3.connect(str(target_db))
    try:
        conn.executescript(
            """
            CREATE TABLE users (
                id VARCHAR(64) PRIMARY KEY,
                username VARCHAR(128) NOT NULL UNIQUE,
                nickname VARCHAR(128) NOT NULL DEFAULT '',
                password_hash VARCHAR(256) NOT NULL,
                preferred_language VARCHAR(16) NOT NULL DEFAULT 'zh-CN',
                avatar_url VARCHAR(512) NOT NULL DEFAULT '',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE user_login_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(64) NOT NULL,
                ip_address VARCHAR(64) NOT NULL DEFAULT '',
                user_agent VARCHAR(512) NOT NULL DEFAULT '',
                login_at DATETIME NOT NULL
            );

            CREATE TABLE classroom_sessions (
                id VARCHAR(64) PRIMARY KEY,
                student_id VARCHAR(64) NOT NULL,
                course_id VARCHAR(64) NOT NULL,
                course_data JSON,
                current_scene_index INTEGER NOT NULL DEFAULT 0,
                visited_scenes JSON,
                quiz_answers JSON,
                chat_history JSON,
                time_spent INTEGER NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                teacher_persona VARCHAR(32) NOT NULL DEFAULT 'expert_mentor',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE daily_routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(64) NOT NULL,
                route_date DATE NOT NULL,
                tasks_json JSON NOT NULL DEFAULT '[]',
                completed_json JSON NOT NULL DEFAULT '[]',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def _seed_json(target_dir: Path) -> dict:
    """Drop a representative fixture of local_storage.json with one row of each kind."""
    payload = {
        "users": [
            {
                "id": 1,
                "username": "teacher",
                "password": "$2b$12$hash",
                "avatar": "https://example/avatar.png",
                "nickname": "老师演示",
                "role": "teacher",
                "display_name": "老师演示",
                "created_at": "2025-01-01T00:00:00",
                "last_login": "2025-02-01T00:00:00",
            },
            {
                "id": 7,
                "username": "alice",
                "password": "$2b$12$hash2",
                "avatar": "",
                "nickname": "Alice",
                "role": "student",
                "display_name": "Alice 同学",
                "created_at": "2025-03-01T00:00:00",
                "last_login": "2025-04-01T00:00:00",
            },
        ],
        "user_login_records": [
            {
                "id": 1,
                "user_id": 1,
                "username": "teacher",
                "success": 1,
                "failure_reason": "",
                "ip_address": "127.0.0.1",
                "user_agent": "Mozilla/5.0",
                "created_at": "2025-02-01T00:00:00",
            },
            {
                "id": 2,
                "user_id": 7,
                "username": "alice",
                "success": 0,
                "failure_reason": "bad password",
                "ip_address": "10.0.0.1",
                "user_agent": "Chrome",
                "created_at": "2025-04-01T00:00:00",
            },
        ],
        "classroom_records": [
            {
                "id": 100,
                "user_id": 7,
                "course_id": "course_rust_001",
                "title": "Rust快速入门",
                "ppt_pages": 29,
                "full_data": '{"courseId": "course_rust_001", "slides": []}',
                "created_at": "2025-04-02T00:00:00",
                "updated_at": "2025-04-02T00:00:00",
            }
        ],
        "daily_routes": [
            {
                "id": 1,
                "user_id": 7,
                "date": "2025-04-02",
                "tasks": [{"task_id": "t1", "title": "看视频"}],
                "completed": ["t1"],
                "generated_at": "2025-04-02T08:00:00",
            }
        ],
        "user_flashcard_progress": [
            {
                "user_id": 7,
                "card_hash": "abc123",
                "course_id": "course_rust_001",
                "chapter_name": "所有权",
                "front": "什么是所有权?",
                "back": "变量绑定的资源管理机制",
                "hint": "看 Box<T>",
                "is_mastered": 1,
                "is_favorite": 0,
                "difficulty": "medium",
                "user_note": "重点",
                "review_count": 3,
            }
        ],
    }
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / "local_storage.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


@pytest.fixture
def fixture_env(tmp_path):
    json_dir = tmp_path / "json"
    db_path = tmp_path / "xingshi_v2.db"
    payload = _seed_json(json_dir)
    _ensure_v2_db_schema(db_path)
    return {"json": json_dir / "local_storage.json", "db": db_path, "payload": payload}


def _row_count(db: Path, table: str) -> int:
    conn = sqlite3.connect(str(db))
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        return cur.fetchone()[0]
    finally:
        conn.close()


def test_migrate_users_inserts_with_id_as_string_and_field_renames(fixture_env):
    """JSON id is int; v2.db users.id is VARCHAR(64). password/avatar get renamed."""
    report = mig.run(json_path=fixture_env["json"], db_path=fixture_env["db"])

    assert report["users_inserted"] == 2
    conn = sqlite3.connect(str(fixture_env["db"]))
    try:
        rows = conn.execute(
            "SELECT id, username, password_hash, avatar_url, nickname FROM users ORDER BY username"
        ).fetchall()
    finally:
        conn.close()
    by_username = {r[1]: r for r in rows}
    # id is stored as string
    assert by_username["teacher"][0] == "1"
    assert by_username["alice"][0] == "7"
    # password → password_hash
    assert by_username["teacher"][2] == "$2b$12$hash"
    # avatar → avatar_url
    assert by_username["teacher"][3] == "https://example/avatar.png"
    # display_name takes priority over nickname for the new nickname column
    assert by_username["teacher"][4] == "老师演示"


def test_migrate_adds_missing_columns_to_user_login_records(fixture_env):
    """ORM v2.db schema only has user_id/ip/user_agent/login_at. db.py and the
    JSON store also carry username/success/failure_reason/created_at. Migration
    adds these columns if missing so the full row can be inserted losslessly."""
    # Pre-check: those columns don't exist in the bare v2 schema fixture
    conn = sqlite3.connect(str(fixture_env["db"]))
    try:
        cols_before = {row[1] for row in conn.execute("PRAGMA table_info(user_login_records)").fetchall()}
    finally:
        conn.close()
    assert "username" not in cols_before
    assert "success" not in cols_before
    assert "failure_reason" not in cols_before
    assert "created_at" not in cols_before

    mig.run(json_path=fixture_env["json"], db_path=fixture_env["db"])

    conn = sqlite3.connect(str(fixture_env["db"]))
    try:
        cols_after = {row[1] for row in conn.execute("PRAGMA table_info(user_login_records)").fetchall()}
    finally:
        conn.close()
    assert {"username", "success", "failure_reason", "created_at"} <= cols_after


def test_migrate_user_login_records_preserves_audit_fields(fixture_env):
    """After migration, login records keep username/success/failure_reason
    and the existing v2.db columns (ip_address, user_agent, login_at,
    created_at) all round-trip from the JSON payload."""
    mig.run(json_path=fixture_env["json"], db_path=fixture_env["db"])

    conn = sqlite3.connect(str(fixture_env["db"]))
    try:
        rows = conn.execute(
            "SELECT user_id, username, success, failure_reason, ip_address, "
            "user_agent, login_at, created_at "
            "FROM user_login_records ORDER BY login_at"
        ).fetchall()
    finally:
        conn.close()
    assert rows == [
        ("1", "teacher", 1, "", "127.0.0.1", "Mozilla/5.0", "2025-02-01T00:00:00", "2025-02-01T00:00:00"),
        ("7", "alice", 0, "bad password", "10.0.0.1", "Chrome", "2025-04-01T00:00:00", "2025-04-01T00:00:00"),
    ]


def test_migrate_classroom_records_maps_to_classroom_sessions(fixture_env):
    """JSON's classroom_records (table name from db.py) lands in v2.db's
    classroom_sessions; full_data → course_data JSON; id int → str."""
    mig.run(json_path=fixture_env["json"], db_path=fixture_env["db"])

    conn = sqlite3.connect(str(fixture_env["db"]))
    try:
        rows = conn.execute(
            "SELECT id, student_id, course_id, course_data, status, current_scene_index "
            "FROM classroom_sessions"
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    rid, student_id, course_id, course_data, status, scene = rows[0]
    # id converted to string
    assert rid == "100"
    # user_id mapped to student_id
    assert student_id == "7"
    assert course_id == "course_rust_001"
    # full_data is stored as JSON text in course_data column
    parsed = json.loads(course_data)
    assert parsed["courseId"] == "course_rust_001"
    # Defaults: status='active', scene index 0 (legacy had no concept of scenes)
    assert status == "active"
    assert scene == 0


def test_migrate_daily_routes_renames_date_field_and_wraps_tasks(fixture_env):
    """JSON 'date' → ORM 'route_date'; 'tasks'/'completed' lists → JSON columns."""
    mig.run(json_path=fixture_env["json"], db_path=fixture_env["db"])

    conn = sqlite3.connect(str(fixture_env["db"]))
    try:
        row = conn.execute(
            "SELECT user_id, route_date, tasks_json, completed_json "
            "FROM daily_routes WHERE user_id = '7'"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    user_id, route_date, tasks_json, completed_json = row
    assert user_id == "7"
    assert route_date == "2025-04-02"
    assert json.loads(tasks_json) == [{"task_id": "t1", "title": "看视频"}]
    assert json.loads(completed_json) == ["t1"]


def test_migrate_creates_user_flashcard_progress_and_inserts(fixture_env):
    """Flashcard table doesn't exist in v2.db; migration must CREATE it and
    rename front/back/hint → front_text/back_text/hint_text per db.py schema."""
    # Pre-check
    conn = sqlite3.connect(str(fixture_env["db"]))
    try:
        exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_flashcard_progress'"
        ).fetchone()
    finally:
        conn.close()
    assert exists is None

    mig.run(json_path=fixture_env["json"], db_path=fixture_env["db"])

    conn = sqlite3.connect(str(fixture_env["db"]))
    try:
        row = conn.execute(
            "SELECT user_id, card_hash, course_id, front_text, back_text, hint_text, "
            "is_mastered, difficulty, review_count "
            "FROM user_flashcard_progress"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    user_id, card_hash, course_id, front_text, back_text, hint_text, is_mastered, difficulty, review_count = row
    assert user_id == "7"
    assert card_hash == "abc123"
    assert course_id == "course_rust_001"
    assert front_text == "什么是所有权?"
    assert back_text == "变量绑定的资源管理机制"
    assert hint_text == "看 Box<T>"
    assert is_mastered == 1
    assert difficulty == "medium"
    assert review_count == 3


def test_migrate_is_idempotent_on_repeat_run(fixture_env):
    """Re-running the migration should not duplicate rows (uses INSERT OR
    IGNORE / ON CONFLICT semantics) and the row counts must stay stable."""
    first = mig.run(json_path=fixture_env["json"], db_path=fixture_env["db"])
    second = mig.run(json_path=fixture_env["json"], db_path=fixture_env["db"])

    assert first["users_inserted"] == 2
    # Second run reports 0 new inserts (rows already present)
    assert second["users_inserted"] == 0
    assert _row_count(fixture_env["db"], "users") == 2
    assert _row_count(fixture_env["db"], "user_login_records") == 2
    assert _row_count(fixture_env["db"], "classroom_sessions") == 1
    assert _row_count(fixture_env["db"], "daily_routes") == 1
    assert _row_count(fixture_env["db"], "user_flashcard_progress") == 1


def test_migrate_handles_empty_json(fixture_env):
    """An empty local_storage.json (zero rows in every collection) is a valid
    no-op — should not error, should produce zero-row tables."""
    fixture_env["json"].write_text(
        json.dumps(
            {
                "users": [],
                "user_login_records": [],
                "classroom_records": [],
                "daily_routes": [],
                "user_flashcard_progress": [],
            }
        ),
        encoding="utf-8",
    )

    report = mig.run(json_path=fixture_env["json"], db_path=fixture_env["db"])

    assert report["status"] == "complete"
    assert report["users_inserted"] == 0
    assert _row_count(fixture_env["db"], "users") == 0


def test_migrate_missing_json_file_returns_error(fixture_env):
    """Missing JSON source → report['status'] == 'error' (no exception)."""
    fixture_env["json"].unlink()

    report = mig.run(json_path=fixture_env["json"], db_path=fixture_env["db"])

    assert report["status"] == "error"
    assert "not found" in report["errors"][0].lower()


def test_migrate_missing_db_file_returns_error(fixture_env):
    """Missing v2.db → report['status'] == 'error' (no exception, no row
    inserts attempted). Mirrors the missing-JSON path coverage."""
    fixture_env["db"].unlink()

    report = mig.run(json_path=fixture_env["json"], db_path=fixture_env["db"])

    assert report["status"] == "error"
    assert "v2.db not found" in report["errors"][0]
    # No rows were attempted (no backup file should exist either)
    assert report["users_inserted"] == 0
    backup_path = Path(report["backup"]) if report.get("backup") else None
    assert backup_path is None or not backup_path.exists()


def test_migrate_creates_timestamped_backup_of_target_db(fixture_env):
    """run() snapshots the target DB before mutating it, matching the
    convention in scripts/migrate_messages_metadata.py."""
    report = mig.run(json_path=fixture_env["json"], db_path=fixture_env["db"])

    assert report["status"] == "complete"
    assert report["backup"] is not None
    backup_path = Path(report["backup"])
    assert backup_path.exists()
    # Backup is a sibling of the target DB with a .backup-<ts> suffix
    assert backup_path.parent == fixture_env["db"].parent
    assert ".backup-" in backup_path.name
