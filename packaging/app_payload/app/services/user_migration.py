"""Application-level helpers for the user table migration.

These wrap the migration script logic for use in:
- M11 dry-run validation
- Manual reconciliation
- CI smoke tests
"""
from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path


def deterministic_uuid(username: str) -> str:
    """Generate a stable UUID for a given username."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"starlearn:{username}"))


def legacy_user_id_to_uuid(legacy_id: int, username: str) -> str:
    """Convert a legacy user.id (int) to ORM users.id (UUID).

    Note: The conversion is by USERNAME, not by legacy_id, to ensure stability
    if legacy_id is reused or changed.
    """
    return deterministic_uuid(username)


def count_legacy_users(legacy_db_path: str) -> int:
    conn = sqlite3.connect(legacy_db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM user")
        return cur.fetchone()[0] or 0
    finally:
        conn.close()


def count_orm_users(orm_db_path: str) -> int:
    conn = sqlite3.connect(orm_db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        return cur.fetchone()[0] or 0
    finally:
        conn.close()


def validate_migration_complete(legacy_db_path: str, orm_db_path: str) -> dict:
    """Check that all legacy users have been migrated to ORM.

    Returns a dict with 'complete' bool and 'unmigrated' list.
    """
    legacy_conn = sqlite3.connect(legacy_db_path)
    orm_conn = sqlite3.connect(orm_db_path)
    try:
        cur_l = legacy_conn.cursor()
        cur_o = orm_conn.cursor()

        cur_l.execute("SELECT username FROM user")
        legacy_usernames = {row[0] for row in cur_l.fetchall()}

        cur_o.execute("SELECT username FROM users")
        orm_usernames = {row[0] for row in cur_o.fetchall()}

        unmigrated = legacy_usernames - orm_usernames

        return {
            "complete": len(unmigrated) == 0,
            "legacy_count": len(legacy_usernames),
            "orm_count": len(orm_usernames),
            "unmigrated_usernames": sorted(unmigrated),
        }
    finally:
        legacy_conn.close()
        orm_conn.close()
