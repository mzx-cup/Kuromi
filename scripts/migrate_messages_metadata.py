"""Idempotent migration: rename db.py 'metadata' TEXT column to 'msg_metadata' JSON.

Runs only on legacy db.py tables. Safe to run multiple times.

Handles SQLite 3.35+ (DROP COLUMN) and older versions (rebuild table).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import shutil
import sys
from datetime import datetime
from pathlib import Path


def backup_database(db_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.with_suffix(f".db.backup-{timestamp}")
    shutil.copy2(db_path, backup_path)
    return backup_path


def table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def migrate(db_path: Path, dry_run: bool = False) -> dict:
    if not db_path.exists():
        return {"status": "skipped", "reason": "db not found"}

    conn = sqlite3.connect(str(db_path))
    try:
        report = {"backup": None, "renamed": False, "rows_migrated": 0}

        if not dry_run:
            report["backup"] = str(backup_database(db_path))

        has_old = table_has_column(conn, "messages", "metadata")
        has_new = table_has_column(conn, "messages", "msg_metadata")

        if has_new and not has_old:
            report["status"] = "already_migrated"
            return report

        if not has_old:
            report["status"] = "no_old_column"
            return report

        if not dry_run:
            cur = conn.cursor()
            # Add new column
            cur.execute("ALTER TABLE messages ADD COLUMN msg_metadata TEXT")

            # Copy data with type conversion. NULL values map to {} so that
            # all rows end up with a valid JSON object (no leftover NULLs).
            cur.execute("SELECT id, metadata FROM messages")
            rows = cur.fetchall()
            for msg_id, old_value in rows:
                if old_value is None:
                    parsed = {}
                else:
                    try:
                        parsed = json.loads(old_value)
                        # If the legacy cell stored a primitive (string/number),
                        # wrap it so the JSON column stays a dict.
                        if not isinstance(parsed, dict):
                            parsed = {"raw": parsed}
                    except (json.JSONDecodeError, TypeError):
                        parsed = {"raw": old_value}
                cur.execute(
                    "UPDATE messages SET msg_metadata = ? WHERE id = ?",
                    (json.dumps(parsed, ensure_ascii=False), msg_id),
                )
            report["rows_migrated"] = len(rows)

            # Drop old column (SQLite 3.35+) or rebuild table
            sqlite_version = tuple(int(x) for x in sqlite3.sqlite_version.split("."))
            if sqlite_version >= (3, 35):
                cur.execute("ALTER TABLE messages DROP COLUMN metadata")
                report["renamed"] = True
            else:
                # Older SQLite: create new table, copy, swap
                cur.execute("""
                    CREATE TABLE messages_new (
                        id INTEGER PRIMARY KEY,
                        user_id TEXT,
                        role TEXT,
                        content TEXT,
                        msg_metadata TEXT,
                        created_at TEXT
                    )
                """)
                cur.execute("""
                    INSERT INTO messages_new (id, user_id, role, content, msg_metadata, created_at)
                    SELECT id, user_id, role, content, msg_metadata, created_at FROM messages
                """)
                cur.execute("DROP TABLE messages")
                cur.execute("ALTER TABLE messages_new RENAME TO messages")
                report["renamed"] = True

            conn.commit()

        report["status"] = "migrated"
        return report
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"Migrating {args.db} (dry_run={args.dry_run})")
    report = migrate(args.db, dry_run=args.dry_run)
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if report["status"] not in ("migrated", "already_migrated", "no_old_column", "skipped"):
        sys.exit(1)


if __name__ == "__main__":
    main()