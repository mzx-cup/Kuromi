"""Final user table unification: merge db.py 'user' (INT PK) into ORM 'users' (VARCHAR PK).

WARNING: This is the most dangerous script in the entire database merge.
Run only after M1-M10 are complete and SLICE_STATUS.md shows all slices done.

Features:
  --dry-run: Print all operations without executing
  --rollback: Restore from backup
  --legacy-db: Path to legacy db.py SQLite
  --orm-db: Path to ORM SQLite
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path


def backup_databases(legacy_db: Path, orm_db: Path) -> dict:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    paths = {
        "legacy_backup": str(legacy_db.with_suffix(f".db.backup-final-{timestamp}")),
        "orm_backup": str(orm_db.with_suffix(f".db.backup-final-{timestamp}")),
    }
    shutil.copy2(legacy_db, paths["legacy_backup"])
    shutil.copy2(orm_db, paths["orm_backup"])
    return paths


def fetch_legacy_users(legacy_db: Path) -> list | None:
    """Returns list of user dicts, or None if the 'user' table doesn't exist."""
    conn = sqlite3.connect(str(legacy_db))
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        if cur.fetchone() is None:
            return None
        cur.execute("SELECT id, username, password, preferred_language FROM user")
        rows = cur.fetchall()
        return [
            {"legacy_id": r[0], "username": r[1], "password_hash": r[2], "preferred_language": r[3]}
            for r in rows
        ]
    finally:
        conn.close()


def generate_uuid_for_user(username: str) -> str:
    """Deterministic UUID for a given username."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"starlearn:{username}"))


def migrate_user_table(legacy_db: Path, orm_db: Path, dry_run: bool = False) -> dict:
    report = {
        "status": "started",
        "backup": None,
        "users_in_legacy": 0,
        "users_migrated": 0,
        "users_already_in_orm": 0,
        "fk_tables_found": [],
        "errors": [],
    }

    if not legacy_db.exists():
        report["status"] = "error"
        report["errors"].append(f"Legacy DB not found: {legacy_db}")
        return report

    if not orm_db.exists():
        report["status"] = "error"
        report["errors"].append(f"ORM DB not found: {orm_db}")
        return report

    users = fetch_legacy_users(legacy_db)
    if users is None:
        report["status"] = "skipped"
        report["errors"].append("legacy 'user' table not found — nothing to migrate")
        return report
    report["users_in_legacy"] = len(users)

    if dry_run:
        report["status"] = "dry_run_complete"
        report["preview"] = {
            "first_3_users": [
                {"legacy_id": u["legacy_id"], "username": u["username"],
                 "new_uuid": generate_uuid_for_user(u["username"])}
                for u in users[:3]
            ]
        }
        return report

    report["backup"] = backup_databases(legacy_db, orm_db)

    # Step 1: Insert ORM users (skip if already exists by username)
    orm_conn = sqlite3.connect(str(orm_db))
    try:
        cur = orm_conn.cursor()
        # Get existing ORM users by username
        cur.execute("SELECT id, username FROM users")
        existing = {row[1]: row[0] for row in cur.fetchall()}
        report["users_already_in_orm"] = len(existing)

        uuid_map = {}  # legacy_id -> new_uuid
        for u in users:
            new_uuid = generate_uuid_for_user(u["username"])
            uuid_map[u["legacy_id"]] = new_uuid

            if u["username"] in existing:
                # User already in ORM; use existing UUID
                uuid_map[u["legacy_id"]] = existing[u["username"]]
                continue

            cur.execute("""
                INSERT OR IGNORE INTO users (id, username, password_hash, preferred_language, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                new_uuid,
                u["username"],
                u["password_hash"],
                u["preferred_language"] or "zh-CN",
                datetime.utcnow().isoformat(),
            ))
            report["users_migrated"] += 1
        orm_conn.commit()
    finally:
        orm_conn.close()

    # Step 2: Audit FK references
    legacy_conn = sqlite3.connect(str(legacy_db))
    try:
        cur = legacy_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        all_tables = [row[0] for row in cur.fetchall()]

        fk_tables = []
        for table in all_tables:
            cur.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in cur.fetchall()]
            if "user_id" in cols:
                # Count rows
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                fk_tables.append({"table": table, "user_id_col_index": cols.index("user_id"),
                                  "row_count": cur.fetchone()[0]})
        report["fk_tables_found"] = fk_tables
    finally:
        legacy_conn.close()

    report["status"] = "complete"
    return report


def rollback(backup_legacy: Path, backup_orm: Path, target_legacy: Path, target_orm: Path) -> dict:
    shutil.copy2(backup_legacy, target_legacy)
    shutil.copy2(backup_orm, target_orm)
    return {"status": "rolled_back"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-db", required=True, type=Path)
    parser.add_argument("--orm-db", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--backup-legacy", type=Path)
    parser.add_argument("--backup-orm", type=Path)
    args = parser.parse_args()

    if args.rollback:
        if not args.backup_legacy or not args.backup_orm:
            print("ERROR: --rollback requires --backup-legacy and --backup-orm")
            sys.exit(1)
        report = rollback(args.backup_legacy, args.backup_orm, args.legacy_db, args.orm_db)
        print(json.dumps(report, indent=2))
        return

    print(f"Migrating user table (dry_run={args.dry_run})")
    report = migrate_user_table(args.legacy_db, args.orm_db, dry_run=args.dry_run)
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if report["status"] not in ("complete", "dry_run_complete", "skipped"):
        sys.exit(1)


if __name__ == "__main__":
    main()
