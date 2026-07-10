"""Audit foreign key references before/after user table unification.

Compares the count of foreign key references to 'user.id' (legacy)
vs 'users.id' (ORM) across all tables in both databases.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def count_fk_references(db_path: Path) -> dict:
    """For each table with user_id, count rows and return mapping."""
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]

        result = {}
        for table in tables:
            cur.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in cur.fetchall()]
            if "user_id" in cols:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                result[table] = cur.fetchone()[0]
        return result
    finally:
        conn.close()


def audit(legacy_db: Path, orm_db: Path) -> dict:
    legacy_refs = count_fk_references(legacy_db)
    orm_refs = count_fk_references(orm_db)

    total_legacy = sum(legacy_refs.values())
    total_orm = sum(orm_refs.values())

    return {
        "legacy_db": str(legacy_db),
        "orm_db": str(orm_db),
        "legacy_references": {"by_table": legacy_refs, "total": total_legacy},
        "orm_references": {"by_table": orm_refs, "total": total_orm},
        "match": total_legacy == total_orm,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-db", required=True, type=Path)
    parser.add_argument("--orm-db", required=True, type=Path)
    args = parser.parse_args()

    report = audit(args.legacy_db, args.orm_db)
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if not report["match"]:
        print("\nWARNING: Reference counts do not match!")
        sys.exit(1)


if __name__ == "__main__":
    main()
