# -*- coding: utf-8 -*-
"""
迁移 user_evaluations / learning_records.user_id 从 INT 改为 VARCHAR(64)

背景：前端 demo 用户 ID 是字符串如 "demo_user_001"，无法写入 INT 列。
这两张表的 user_id 仅作记录用途，与 user.id 的 FK 强约束反而阻止了 demo 用户的写入。
迁移步骤：
  1) 去掉指向 user.id 的 FK（demo 用户本来就不在 user 表）
  2) 列类型 INT → VARCHAR(64)（现有整数记录会自动转换为字符串，无损）
  3) 若已是 VARCHAR 则跳过（幂等）

幂等：重复运行不会报错也不会丢失数据。
"""

from __future__ import annotations

import sys

import db


TARGET_TABLES = ["user_evaluations", "learning_records"]
TARGET_COLUMN = "user_id"
NEW_TYPE = "VARCHAR(64)"


def _column_type(conn, table: str, column: str) -> str | None:
    cur = conn.cursor()
    cur.execute(
        """SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
           FROM information_schema.COLUMNS
           WHERE TABLE_SCHEMA = DATABASE()
             AND TABLE_NAME   = %s
             AND COLUMN_NAME  = %s""",
        (table, column),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    data_type, max_len = row
    if data_type.lower() in ("varchar", "char"):
        return f"{data_type}({max_len})"
    return data_type.upper()


def _drop_fk_if_exists(conn, table: str) -> str:
    """Drop the FK constraint on user_id if it points to user.id (or anywhere)."""
    cur = conn.cursor()
    cur.execute(
        """SELECT CONSTRAINT_NAME
           FROM information_schema.KEY_COLUMN_USAGE
           WHERE TABLE_SCHEMA = DATABASE()
             AND TABLE_NAME   = %s
             AND COLUMN_NAME  = %s
             AND REFERENCED_TABLE_NAME IS NOT NULL""",
        (table, TARGET_COLUMN),
    )
    fks = [r[0] for r in cur.fetchall()]
    for fk in fks:
        cur.execute(f"ALTER TABLE `{table}` DROP FOREIGN KEY `{fk}`")
    cur.close()
    return ", ".join(fks) if fks else "(none)"


def migrate_table(conn, table: str) -> dict:
    cur_type = _column_type(conn, table, TARGET_COLUMN)
    cur = conn.cursor()
    try:
        cur.execute("START TRANSACTION")
        if cur_type and cur_type.upper() == NEW_TYPE.upper():
            cur.execute("COMMIT")
            return {"table": table, "action": "skip", "current": cur_type}

        # 1) drop FK
        dropped_fk = _drop_fk_if_exists(conn, table)

        # 2) change column type
        cur.execute(
            f"ALTER TABLE `{table}` MODIFY COLUMN `{TARGET_COLUMN}` {NEW_TYPE} NOT NULL"
        )

        cur.execute("COMMIT")
        return {
            "table": table,
            "action": "migrated",
            "from": cur_type,
            "to": NEW_TYPE,
            "dropped_fk": dropped_fk,
        }
    except Exception as exc:
        cur.execute("ROLLBACK")
        raise
    finally:
        cur.close()


def main():
    sys.stdout.write("Detecting backend ... ")
    backend = db._detect_backend()
    print(backend)
    if backend != "mysql":
        print("[migrate] SQLite/JSON backend does not enforce user_id column types; nothing to do.")
        return 0

    with db.get_db() as conn:
        if conn is None:
            print("[migrate] No DB connection available.")
            return 1
        for table in TARGET_TABLES:
            try:
                result = migrate_table(conn, table)
                print(f"[migrate] {result}")
            except Exception as exc:
                print(f"[migrate] FAILED on {table}: {exc}")
                return 2

    print("\n[migrate] Verifying final schema ...")
    with db.get_db() as conn:
        cur = conn.cursor()
        for table in TARGET_TABLES:
            cur.execute(
                """SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                   FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE()
                     AND TABLE_NAME = %s
                     AND COLUMN_NAME = %s""",
                (table, TARGET_COLUMN),
            )
            print(f"  {table}.{TARGET_COLUMN} = {cur.fetchone()}")
        cur.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
