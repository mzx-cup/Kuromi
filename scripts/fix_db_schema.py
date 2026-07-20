# -*- coding: utf-8 -*-
"""Fix SQLite database schema to be compatible with legacy db.py code."""

import sqlite3
import os
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'xingshi.db')

MIGRATIONS = {
    "user_evaluations": [
        "ALTER TABLE user_evaluations ADD COLUMN interaction_count INTEGER DEFAULT 0",
        "ALTER TABLE user_evaluations ADD COLUMN socratic_pass_rate REAL DEFAULT 0.0",
        "ALTER TABLE user_evaluations ADD COLUMN difficulty_level TEXT DEFAULT 'basic'",
        "ALTER TABLE user_evaluations ADD COLUMN code_practice_time INTEGER DEFAULT 0",
        "ALTER TABLE user_evaluations ADD COLUMN focus_time_today INTEGER DEFAULT 0",
        "ALTER TABLE user_evaluations ADD COLUMN flashcards_studied INTEGER DEFAULT 0",
        "ALTER TABLE user_evaluations ADD COLUMN streak_days INTEGER DEFAULT 0",
        "ALTER TABLE user_evaluations ADD COLUMN eval_json TEXT",
        "ALTER TABLE user_evaluations ADD COLUMN record_date TEXT",
        "ALTER TABLE user_evaluations ADD COLUMN created_at TEXT DEFAULT (datetime('now','localtime'))",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_eval_user_date ON user_evaluations (user_id, record_date)",
    ],
    "user_stats": [
        "ALTER TABLE user_stats ADD COLUMN stats_json TEXT",
        "ALTER TABLE user_stats ADD COLUMN created_at TEXT DEFAULT (datetime('now','localtime'))",
        "ALTER TABLE user_stats ADD COLUMN updated_at TEXT DEFAULT (datetime('now','localtime'))",
    ],
    "user_focus_history": [
        "ALTER TABLE user_focus_history ADD COLUMN focus_json TEXT",
        "ALTER TABLE user_focus_history ADD COLUMN updated_at TEXT DEFAULT (datetime('now','localtime'))",
    ],
    "messages": [
        "ALTER TABLE messages ADD COLUMN metadata TEXT",
    ],
    "learning_records": [
        "ALTER TABLE learning_records ADD COLUMN interaction_count INTEGER DEFAULT 0",
        "ALTER TABLE learning_records ADD COLUMN code_practice_time INTEGER DEFAULT 0",
        "ALTER TABLE learning_records ADD COLUMN socratic_pass_rate REAL DEFAULT 0.0",
        "ALTER TABLE learning_records ADD COLUMN difficulty_level TEXT DEFAULT 'basic'",
        "ALTER TABLE learning_records ADD COLUMN profile_json TEXT",
        "ALTER TABLE learning_records ADD COLUMN created_at TEXT DEFAULT (datetime('now','localtime'))",
        "ALTER TABLE learning_records ADD COLUMN updated_at TEXT DEFAULT (datetime('now','localtime'))",
    ],
    "user_profile": [
        "ALTER TABLE user_profile ADD COLUMN profile_json TEXT",
        "ALTER TABLE user_profile ADD COLUMN evaluation_json TEXT",
        "ALTER TABLE user_profile ADD COLUMN last_grade_record TEXT",
        "ALTER TABLE user_profile ADD COLUMN created_at TEXT DEFAULT (datetime('now','localtime'))",
        "ALTER TABLE user_profile ADD COLUMN updated_at TEXT DEFAULT (datetime('now','localtime'))",
    ],
    "user_preferences": [
        "ALTER TABLE user_preferences ADD COLUMN preferences_json TEXT",
    ],
    "user_achievements": [
        "ALTER TABLE user_achievements ADD COLUMN achievements_json TEXT",
    ],
    "user_settings": [
        "ALTER TABLE user_settings ADD COLUMN settings_json TEXT",
        "ALTER TABLE user_settings ADD COLUMN weather_city TEXT DEFAULT ''",
        "ALTER TABLE user_settings ADD COLUMN floating_alarm_x INTEGER",
        "ALTER TABLE user_settings ADD COLUMN floating_alarm_y INTEGER",
        "ALTER TABLE user_settings ADD COLUMN hub_theme TEXT DEFAULT 'light'",
        "ALTER TABLE user_settings ADD COLUMN created_at TEXT DEFAULT (datetime('now','localtime'))",
        "ALTER TABLE user_settings ADD COLUMN updated_at TEXT DEFAULT (datetime('now','localtime'))",
    ],
}


def run_migration():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database file not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    fixed = 0
    skipped = 0
    failed = 0

    for table, alters in MIGRATIONS.items():
        print(f"\n[{table}]")
        for sql in alters:
            try:
                conn.execute(sql)
                conn.commit()
                short = sql[:80] + "..." if len(sql) > 80 else sql
                print(f"  [OK] {short}")
                fixed += 1
            except sqlite3.OperationalError as e:
                err_msg = str(e)
                if "duplicate column name" in err_msg or "already exists" in err_msg:
                    print(f"  [SKIP] Already exists: {sql[:60]}...")
                    skipped += 1
                else:
                    print(f"  [FAIL] {err_msg}")
                    failed += 1
            except Exception as e:
                print(f"  [FAIL] {e}")
                failed += 1

    conn.close()

    print(f"\n{'='*60}")
    print(f"  Done: {fixed} added, {skipped} skipped, {failed} failed")
    print(f"{'='*60}")

    if failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    run_migration()
