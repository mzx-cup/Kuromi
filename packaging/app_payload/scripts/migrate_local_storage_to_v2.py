"""One-shot migration: local_storage.json → xingshi_v2.db.

Phase 2.1 of the demo-account / data-merge plan. Reads the JSON file the
frontend currently persists and writes its rows into the ORM-managed
SQLite (or MySQL — SQLite is the supported dev target) under
xingshi_v2.db. Once executed, ``local_storage.json`` can be archived:
all subsequent reads/writes go through the ORM repositories.

Maps (the four ORM tables are assumed to pre-exist; only
``user_flashcard_progress`` is created on demand):
    users                    → users                       (id int→str,
                                                               password→password_hash,
                                                               avatar→avatar_url)
    user_login_records       → user_login_records          (ALTER TABLE to add
                                                               username / success /
                                                               failure_reason /
                                                               created_at;
                                                               id auto-assigned to avoid
                                                               clashing with existing
                                                               AUTOINCREMENT PKs)
    classroom_records        → classroom_sessions          (id int→str;
                                                               full_data → course_data JSON)
    daily_routes             → daily_routes                (date → route_date;
                                                               tasks / completed → *_json)
    user_flashcard_progress  → user_flashcard_progress     (CREATE TABLE; front/back/hint
                                                               renamed to *_text)

The script is idempotent — uses INSERT OR IGNORE / ON CONFLICT semantics on
every row. Re-running on the same v2.db is a safe no-op (no duplicate rows,
no destructive changes). A timestamped backup of the target DB is created
before any schema or row mutation, matching the convention used by the
other repo migration scripts (migrate_messages_metadata.py,
migrate_user_table.py).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


# ---------- helpers ----------

def _table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    )
    return cur.fetchone() is not None


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    """Run ALTER TABLE ADD COLUMN if the column is not already present."""
    if _table_has_column(conn, table, column):
        return
    cur = conn.cursor()
    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _now_iso() -> str:
    return datetime.utcnow().isoformat(sep=" ", timespec="seconds")


def _backup_database(db_path: Path) -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.with_suffix(f".db.backup-{timestamp}")
    shutil.copy2(db_path, backup_path)
    return backup_path


# ---------- migration steps ----------

def _ensure_login_record_columns(conn: sqlite3.Connection) -> None:
    """v2.db's user_login_records only has user_id/ip_address/user_agent/login_at.
    db.py's full schema also has username/success/failure_reason/created_at.
    We add the missing columns so the JSON payload can land losslessly."""
    _add_column_if_missing(conn, "user_login_records", "username", "VARCHAR(128) DEFAULT ''")
    _add_column_if_missing(conn, "user_login_records", "success", "INTEGER DEFAULT 0")
    _add_column_if_missing(conn, "user_login_records", "failure_reason", "VARCHAR(255) DEFAULT ''")
    _add_column_if_missing(conn, "user_login_records", "created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")


def _ensure_flashcard_table(conn: sqlite3.Connection) -> None:
    """user_flashcard_progress is not in the ORM schema; create it from the
    db.py CREATE TABLE definition so the JSON progress rows have a home."""
    if _table_exists(conn, "user_flashcard_progress"):
        return
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE user_flashcard_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id VARCHAR(64) NOT NULL,
            card_hash TEXT NOT NULL,
            course_id TEXT NOT NULL DEFAULT 'bigdata',
            chapter_name TEXT NOT NULL DEFAULT '',
            front_text TEXT NOT NULL DEFAULT '',
            back_text TEXT NOT NULL DEFAULT '',
            hint_text TEXT NOT NULL DEFAULT '',
            is_mastered INTEGER NOT NULL DEFAULT 0,
            is_favorite INTEGER NOT NULL DEFAULT 0,
            difficulty TEXT NOT NULL DEFAULT 'medium',
            user_note TEXT NOT NULL DEFAULT '',
            review_count INTEGER NOT NULL DEFAULT 0,
            first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_reviewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, card_hash)
        )
        """
    )


def _migrate_users(conn: sqlite3.Connection, users: list[dict]) -> int:
    cur = conn.cursor()
    inserted = 0
    for u in users:
        new_id = str(u["id"])
        cur.execute(
            """
            INSERT OR IGNORE INTO users
                (id, username, password_hash, preferred_language, avatar_url, nickname)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id,
                u.get("username", ""),
                u.get("password", ""),
                u.get("preferred_language") or "zh-CN",
                u.get("avatar", ""),
                # display_name is the post-login label; nickname is the db.py column
                u.get("display_name") or u.get("nickname") or "",
            ),
        )
        inserted += int(cur.rowcount > 0)
    return inserted


def _migrate_login_records(conn: sqlite3.Connection, records: list[dict]) -> int:
    cur = conn.cursor()
    inserted = 0
    for r in records:
        # The JSON id is a positional counter (len(records) + 1 in db.py);
        # the ORM PK is AUTOINCREMENT. If we carried the JSON id explicitly,
        # INSERT OR IGNORE would silently drop rows that collide with
        # existing autoincremented ids. Let the DB assign a fresh id.
        occurred_at = r.get("created_at") or _now_iso()
        # No natural unique key in the JSON rows; guard on (user_id, login_at,
        # ip) so re-running the migration is a no-op. The ORM table has no
        # unique constraint we can lean on.
        cur.execute(
            """
            SELECT 1 FROM user_login_records
            WHERE user_id = ? AND login_at = ? AND ip_address = ?
            """,
            (str(r["user_id"]), occurred_at, r.get("ip_address", "")),
        )
        if cur.fetchone() is not None:
            continue
        cur.execute(
            """
            INSERT INTO user_login_records
                (user_id, username, success, failure_reason,
                 ip_address, user_agent, login_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(r["user_id"]),
                r.get("username", ""),
                int(r.get("success", 0)),
                r.get("failure_reason", ""),
                r.get("ip_address", ""),
                r.get("user_agent", ""),
                occurred_at,
                occurred_at,
            ),
        )
        inserted += 1
    return inserted


def _migrate_classroom_records(conn: sqlite3.Connection, records: list[dict]) -> int:
    cur = conn.cursor()
    inserted = 0
    for r in records:
        new_id = str(r["id"])
        # course_data column holds the full_data JSON blob; other JSON columns
        # are nullable defaults (the legacy class had no scene/quiz concept).
        # classroom_sessions.time_spent / current_slide / teacher_mode are
        # NOT NULL with no DB default; provide 0/false to keep the INSERT
        # valid (and prevent INSERT OR IGNORE from silently swallowing it).
        full_data = r.get("full_data") or "{}"
        cur.execute(
            """
            INSERT OR IGNORE INTO classroom_sessions
                (id, student_id, course_id, course_data,
                 current_scene_index, time_spent, status, teacher_persona,
                 current_slide, teacher_mode)
            VALUES (?, ?, ?, ?, 0, 0, 'active', 'expert_mentor', 0, 0)
            """,
            (
                new_id,
                str(r["user_id"]),
                r.get("course_id", ""),
                full_data,
            ),
        )
        inserted += int(cur.rowcount > 0)
    return inserted


def _migrate_daily_routes(conn: sqlite3.Connection, routes: list[dict]) -> int:
    cur = conn.cursor()
    inserted = 0
    for r in routes:
        tasks_json = json.dumps(r.get("tasks", []), ensure_ascii=False)
        completed_json = json.dumps(r.get("completed", []), ensure_ascii=False)
        # No natural unique key in the JSON rows, so we accept re-inserts by
        # guarding with a SELECT first. The migration is a one-shot anyway.
        cur.execute(
            "SELECT 1 FROM daily_routes WHERE user_id = ? AND route_date = ?",
            (str(r["user_id"]), r.get("date", "")),
        )
        if cur.fetchone() is not None:
            continue
        # daily_routes.created_at is NOT NULL without a DB default in v2.db;
        # fall back to the JSON's generated_at, or now() if absent.
        created_at = r.get("generated_at") or _now_iso()
        cur.execute(
            """
            INSERT INTO daily_routes
                (user_id, route_date, tasks_json, completed_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (str(r["user_id"]), r.get("date", ""), tasks_json, completed_json, created_at),
        )
        inserted += 1
    return inserted


def _migrate_flashcard_progress(conn: sqlite3.Connection, cards: list[dict]) -> int:
    cur = conn.cursor()
    inserted = 0
    for c in cards:
        cur.execute(
            """
            INSERT OR IGNORE INTO user_flashcard_progress
                (user_id, card_hash, course_id, chapter_name,
                 front_text, back_text, hint_text,
                 is_mastered, is_favorite, difficulty, user_note, review_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(c["user_id"]),
                c.get("card_hash", ""),
                c.get("course_id", "bigdata"),
                c.get("chapter_name", ""),
                c.get("front", ""),
                c.get("back", ""),
                c.get("hint", ""),
                int(c.get("is_mastered", 0)),
                int(c.get("is_favorite", 0)),
                c.get("difficulty", "medium"),
                c.get("user_note", ""),
                int(c.get("review_count", 0)),
            ),
        )
        inserted += int(cur.rowcount > 0)
    return inserted


# ---------- public entrypoint ----------

def run(json_path: Path, db_path: Path) -> dict:
    """Run the full migration. Returns a report dict with per-table counts
    and a top-level 'status' field. Never raises — errors go into the
    report so the caller (CLI / smoke test) can decide what to do."""
    report: dict = {
        "status": "started",
        "json_path": str(json_path),
        "db_path": str(db_path),
        "backup": None,
        "users_inserted": 0,
        "user_login_records_inserted": 0,
        "classroom_sessions_inserted": 0,
        "daily_routes_inserted": 0,
        "user_flashcard_progress_inserted": 0,
        "errors": [],
    }

    if not json_path.exists():
        report["status"] = "error"
        report["errors"].append(f"JSON source not found: {json_path}")
        return report

    if not db_path.exists():
        report["status"] = "error"
        report["errors"].append(f"v2.db not found: {db_path}")
        return report

    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        report["status"] = "error"
        report["errors"].append(f"Failed to read JSON: {e}")
        return report

    # Schema/row mutations are non-destructive, but we still snapshot the
    # target DB first — matches the convention in
    # scripts/migrate_messages_metadata.py and scripts/migrate_user_table.py.
    report["backup"] = str(_backup_database(db_path))

    conn = sqlite3.connect(str(db_path))
    try:
        _ensure_login_record_columns(conn)
        _ensure_flashcard_table(conn)
        conn.commit()

        report["users_inserted"] = _migrate_users(conn, payload.get("users", []))
        report["user_login_records_inserted"] = _migrate_login_records(
            conn, payload.get("user_login_records", [])
        )
        report["classroom_sessions_inserted"] = _migrate_classroom_records(
            conn, payload.get("classroom_records", [])
        )
        report["daily_routes_inserted"] = _migrate_daily_routes(
            conn, payload.get("daily_routes", [])
        )
        report["user_flashcard_progress_inserted"] = _migrate_flashcard_progress(
            conn, payload.get("user_flashcard_progress", [])
        )
        conn.commit()
    except Exception as e:  # noqa: BLE001 — surface any failure to the report
        report["status"] = "error"
        report["errors"].append(f"Migration failed: {e}")
        conn.rollback()
        return report
    finally:
        conn.close()

    report["status"] = "complete"
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, type=Path)
    parser.add_argument("--db", required=True, type=Path)
    args = parser.parse_args()

    report = run(args.json, args.db)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if report["status"] != "complete":
        sys.exit(1)


if __name__ == "__main__":
    main()
