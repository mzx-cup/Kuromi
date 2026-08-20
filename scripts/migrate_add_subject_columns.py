# -*- coding: utf-8 -*-
"""
为 learning_records / study_sessions 补 subject 列。

背景：
  app/repositories/legacy/capability.py 在 6 维画像聚合时使用
      SELECT subject, SUM(minutes) FROM learning_records GROUP BY subject
      SELECT subject, SUM(duration_minutes) FROM study_sessions GROUP BY subject
  但 init_sqlite.sql / init_xingshi_v2_mysql.sql / Navicat/setup_database.py 中
  learning_records 没有 subject 列，导致前端调用 /api/agents/execute 时
  backend 报 "no such column: subject"，画像降级为空。

本脚本：
  - 给 learning_records 加 subject VARCHAR(64) NOT NULL DEFAULT ''
  - 给 study_sessions 已有 subject 的情况下也保证列存在（幂等补全）
  - SQLite / MySQL 双库兼容
  - 重复运行安全
"""

from __future__ import annotations

import os
import sys

# 允许从 scripts/ 子目录直接执行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db


def _column_exists(conn, table: str, column: str, is_sqlite: bool) -> bool:
    cur = conn.cursor()
    try:
        if is_sqlite:
            cur.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in cur.fetchall()]
        else:
            cur.execute(
                """SELECT COLUMN_NAME FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE()
                     AND TABLE_NAME   = %s
                     AND COLUMN_NAME  = %s""",
                (table, column),
            )
            cols = [r[0] for r in cur.fetchall()]
    finally:
        cur.close()
    return column in cols


def _add_column(conn, table: str, column: str, ddl: str, is_sqlite: bool) -> str:
    """DDL 形如 'VARCHAR(64) NOT NULL DEFAULT ''' 或 'VARCHAR(64) DEFAULT '''."""
    cur = conn.cursor()
    try:
        if is_sqlite:
            # SQLite ALTER TABLE ADD COLUMN 不支持完整约束，只能写简单类型
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        else:
            cur.execute(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {ddl}")
        conn.commit()
        return "added"
    finally:
        cur.close()


# 目标：(表, 列, MySQL DDL, SQLite DDL)
TARGETS = [
    ("learning_records", "subject",
     "VARCHAR(64) NOT NULL DEFAULT ''",
     "TEXT NOT NULL DEFAULT ''"),
    ("study_sessions", "subject",
     "VARCHAR(64) NOT NULL DEFAULT ''",
     "TEXT NOT NULL DEFAULT ''"),
]


def main() -> int:
    backend = db._detect_backend()
    print(f"Detecting backend ... {backend}")

    if backend == "sqlite":
        is_sqlite = True
    elif backend == "mysql":
        is_sqlite = False
    else:
        print("[migrate_subject] Unknown backend, nothing to do.")
        return 0

    with db.get_db() as conn:
        if conn is None:
            print("[migrate_subject] No DB connection available.")
            return 1
        for table, column, mysql_ddl, sqlite_ddl in TARGETS:
            try:
                if _column_exists(conn, table, column, is_sqlite):
                    print(f"[migrate_subject] {table}.{column} already exists, skip.")
                    continue
                ddl = sqlite_ddl if is_sqlite else mysql_ddl
                action = _add_column(conn, table, column, ddl, is_sqlite)
                print(f"[migrate_subject] {table}.{column} -> {action}")
            except Exception as exc:
                print(f"[migrate_subject] FAILED on {table}.{column}: {exc}")
                return 2

    print("\n[migrate_subject] Verifying final schema ...")
    with db.get_db() as conn:
        cur = conn.cursor()
        for table, column, *_ in TARGETS:
            if is_sqlite:
                cur.execute(f"PRAGMA table_info({table})")
                row = next((r for r in cur.fetchall() if r[1] == column), None)
            else:
                cur.execute(
                    """SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                       FROM information_schema.COLUMNS
                       WHERE TABLE_SCHEMA = DATABASE()
                         AND TABLE_NAME = %s
                         AND COLUMN_NAME = %s""",
                    (table, column),
                )
                row = cur.fetchone()
            print(f"  {table}.{column} = {row}")
        cur.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
