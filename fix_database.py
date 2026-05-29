"""
星识 (Star-Learn) 数据库修复脚本
自动检测并修复缺失的表和列

用法:
  python fix_database.py
"""
import os
import sys

# 复用 setup_database.py 的配置
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Navicat'))
from setup_database import (
    MYSQL_CONFIG, DATABASE_NAME, detect_backend,
    MYSQL_TABLES, TABLE_NAMES, mysql_to_sqlite
)


def _is_sqlite(conn):
    return hasattr(conn, 'sqlite_version')


def fix_mysql():
    try:
        import pymysql
    except ImportError:
        print("错误: 未安装 pymysql，请运行: pip install pymysql")
        return False

    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"USE {DATABASE_NAME}")
        print(f"已连接到数据库: {DATABASE_NAME}")
    except Exception as e:
        print(f"连接 MySQL 失败: {e}")
        return False

    fixed = 0

    # 1. 检查并创建缺失的表
    for i, sql in enumerate(MYSQL_TABLES):
        table_name = TABLE_NAMES[i]
        try:
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            if cursor.fetchone():
                print(f"  [OK] {table_name:35s} 已存在")
            else:
                cursor.execute(sql)
                print(f"  [FIX] {table_name:35s} 已创建")
                fixed += 1
        except Exception as e:
            print(f"  [FAIL] {table_name:35s} 错误: {e}")

    # 2. 检查 learning_path 表的 generated_at 列
    try:
        cursor.execute("SHOW COLUMNS FROM learning_path LIKE 'generated_at'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE learning_path ADD COLUMN generated_at DATETIME DEFAULT NULL")
            print(f"  [FIX] learning_path.generated_at          已添加")
            fixed += 1
        else:
            print(f"  [OK] learning_path.generated_at           已存在")
    except Exception as e:
        print(f"  [FAIL] learning_path.generated_at         错误: {e}")

    # 3. 检查 classroom_sessions 表的 teacher_persona 列
    try:
        cursor.execute("SHOW COLUMNS FROM classroom_sessions LIKE 'teacher_persona'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE classroom_sessions ADD COLUMN teacher_persona VARCHAR(32) NOT NULL DEFAULT 'expert_mentor'")
            print(f"  [FIX] classroom_sessions.teacher_persona  已添加")
            fixed += 1
        else:
            print(f"  [OK] classroom_sessions.teacher_persona   已存在")
    except Exception as e:
        print(f"  [FAIL] classroom_sessions.teacher_persona 错误: {e}")

    conn.commit()
    cursor.close()
    conn.close()

    if fixed > 0:
        print(f"\n修复完成! 共修复 {fixed} 项。")
    else:
        print("\n所有表和列都正常，无需修复。")
    return True


def fix_sqlite():
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), 'Navicat', 'xingshi.db')
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(__file__), 'xingshi.db')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"已连接到 SQLite: {db_path}")

    fixed = 0

    # 1. 检查并创建缺失的表
    for i, sql in enumerate(MYSQL_TABLES):
        table_name = TABLE_NAMES[i]
        try:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if cursor.fetchone():
                print(f"  [OK] {table_name:35s} 已存在")
            else:
                sqlite_sql, extra_indices = mysql_to_sqlite(sql)
                cursor.execute(sqlite_sql)
                for idx_sql in extra_indices:
                    try:
                        cursor.execute(idx_sql)
                    except Exception:
                        pass
                print(f"  [FIX] {table_name:35s} 已创建")
                fixed += 1
        except Exception as e:
            print(f"  [FAIL] {table_name:35s} 错误: {e}")

    # 2. 检查 learning_path 表的 generated_at 列
    try:
        cursor.execute("PRAGMA table_info(learning_path)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'generated_at' not in columns:
            cursor.execute("ALTER TABLE learning_path ADD COLUMN generated_at TEXT")
            print(f"  [FIX] learning_path.generated_at          已添加")
            fixed += 1
        else:
            print(f"  [OK] learning_path.generated_at           已存在")
    except Exception as e:
        print(f"  [FAIL] learning_path.generated_at         错误: {e}")

    # 3. 检查 classroom_sessions 表的 teacher_persona 列
    try:
        cursor.execute("PRAGMA table_info(classroom_sessions)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'teacher_persona' not in columns:
            cursor.execute("ALTER TABLE classroom_sessions ADD COLUMN teacher_persona TEXT NOT NULL DEFAULT 'expert_mentor'")
            print(f"  [FIX] classroom_sessions.teacher_persona  已添加")
            fixed += 1
        else:
            print(f"  [OK] classroom_sessions.teacher_persona   已存在")
    except Exception as e:
        print(f"  [FAIL] classroom_sessions.teacher_persona 错误: {e}")

    conn.commit()
    conn.close()

    if fixed > 0:
        print(f"\n修复完成! 共修复 {fixed} 项。")
    else:
        print("\n所有表和列都正常，无需修复。")
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("  星识 (Star-Learn) 数据库修复脚本")
    print("=" * 60)

    backend = detect_backend()
    print(f"\n检测到后端: {backend.upper()}\n")

    if backend == 'mysql':
        success = fix_mysql()
    else:
        success = fix_sqlite()

    if success:
        print("\n提示: 修复完成后请重新启动后端服务 (python main.py)")
    else:
        sys.exit(1)
