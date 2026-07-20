"""Reconcile two database backends and report inconsistencies.

Usage:
  python scripts/reconcile_databases.py --primary xingshi.db --shadow xingshi_v2.db --tables user_preferences
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


NOISE_FIELDS = {"updated_at", "created_at", "last_synced_at", "login_at"}


def fetch_table(db_path: Path, table: str) -> dict:
    """Return {row_id: row_dict} for given table."""
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table}")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return {
            str(row[0]): dict(zip(cols, row))
            for row in rows
        }
    except sqlite3.OperationalError as e:
        return {"__error__": str(e)}
    finally:
        conn.close()


def normalize_row(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in NOISE_FIELDS}


def rows_equal(a: dict, b: dict) -> bool:
    return normalize_row(a) == normalize_row(b)


def reconcile_table(table: str, primary_path: Path, shadow_path: Path) -> dict:
    primary = fetch_table(primary_path, table)
    shadow = fetch_table(shadow_path, table)

    if "__error__" in primary:
        return {"table": table, "error": primary["__error__"]}
    if "__error__" in shadow:
        return {"table": table, "error": shadow["__error__"]}

    primary_ids = set(primary.keys())
    shadow_ids = set(shadow.keys())

    missing_in_shadow = primary_ids - shadow_ids
    extra_in_shadow = shadow_ids - primary_ids

    divergent = []
    for id_ in primary_ids & shadow_ids:
        if not rows_equal(primary[id_], shadow[id_]):
            divergent.append({
                "id": id_,
                "primary": normalize_row(primary[id_]),
                "shadow": normalize_row(shadow[id_]),
            })

    return {
        "table": table,
        "primary_count": len(primary_ids),
        "shadow_count": len(shadow_ids),
        "missing_in_shadow": sorted(missing_in_shadow),
        "extra_in_shadow": sorted(extra_in_shadow),
        "divergent": divergent,
        "consistent": not (missing_in_shadow or extra_in_shadow or divergent),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary", required=True, type=Path)
    parser.add_argument("--shadow", required=True, type=Path)
    parser.add_argument("--tables", required=True, help="Comma-separated table names")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    tables = args.tables.split(",")
    results = {
        "date": datetime.now().isoformat(),
        "primary": str(args.primary),
        "shadow": str(args.shadow),
        "tables": [reconcile_table(t.strip(), args.primary, args.shadow) for t in tables],
    }

    print(json.dumps(results, indent=2, ensure_ascii=False))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    inconsistent = [r for r in results["tables"] if not r.get("consistent", True)]
    if inconsistent:
        sys.exit(1)


if __name__ == "__main__":
    main()