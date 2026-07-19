"""迁移脚本：为已有数据库添加缺失的 user_memories 表（同步版本）"""
import sys
import os
import sqlite3

# 直接指定数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "xingshi.db")


def migrate():
    print(f"[migrate] 使用数据库: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_memories'")
    if cursor.fetchone():
        print("[migrate] user_memories 表已存在，无需迁移")
        conn.close()
        return

    # 创建表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id VARCHAR(64) NOT NULL,
            memory_type VARCHAR(32) DEFAULT 'fact',
            content TEXT DEFAULT '',
            importance INTEGER DEFAULT 1,
            source_conversation_id VARCHAR(64),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP,
            confirmed INTEGER DEFAULT 0,
            access_count INTEGER DEFAULT 1
        )
    """)
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_memories_user_id ON user_memories(user_id)")
    conn.commit()
    conn.close()
    print("[migrate] user_memories 表创建成功")


if __name__ == "__main__":
    migrate()
