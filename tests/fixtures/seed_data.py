"""Seed data generators for dual-backend testing.

Provides consistent data across legacy db.py schema and ORM schema.

真实 schema 修复（split-brain 整改的一部分）：``init_legacy_schema`` 不再
手写"想象中的"表结构，而是重放 **生产 layer-1 SQLite 库
（storage/xingshi.db）的真实 DDL**（见 ``real_legacy_schema.sql``，
从真实库 sqlite_master 导出）。此前 fixture 里的
``user_preferences(user_id, key, value)`` / ``user_themes`` /
``knowledge_reviews`` 等表在真实引擎中并不存在，导致测试永远在验证
一个假想世界 —— repo 对真实库"查找不到数据"的问题被测试完全掩盖。

ORM(v2) 侧的 course_progress / learning_paths 等归一化表由
``init_orm_course_tables`` 单独建（它们的数据家是 xingshi_v2.db，
与 layer-1 的 user_evaluations / learning_path 是**同名不同形**的表，
不能混在同一个 fixture 文件里创建）。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

_SCHEMA_DIR = Path(__file__).parent

# Canonical seed dataset
SEED_USERS = [
    {"id": 1, "username": "alice", "password": "hashed_pw_1", "preferred_language": "zh-CN"},
    {"id": 2, "username": "bob", "password": "hashed_pw_2", "preferred_language": "en-US"},
    {"id": 3, "username": "charlie", "password": "hashed_pw_3", "preferred_language": "zh-CN"},
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()


def init_legacy_schema(db_path: str) -> None:
    """Create the REAL layer-1 schema (replayed from storage/xingshi.db DDL)."""
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript((_SCHEMA_DIR / "real_legacy_schema.sql").read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


# ORM(v2) 归一化表的建表 DDL —— 镜像 ORM ``create_all`` 在 xingshi_v2.db
# 里生成的形状（state_json 列名、无 UNIQUE(user_id, course_id)）。
_ORM_COURSE_DDL = """
CREATE TABLE IF NOT EXISTS course_progress (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    course_id VARCHAR(64) NOT NULL,
    progress_percent FLOAT NOT NULL,
    completed_at DATETIME,
    last_accessed DATETIME NOT NULL,
    state_json JSON NOT NULL
);
CREATE TABLE IF NOT EXISTS learning_paths (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    name VARCHAR(256),
    description TEXT,
    status VARCHAR(32),
    created_at DATETIME
);
CREATE TABLE IF NOT EXISTS learning_path_nodes (
    id INTEGER NOT NULL PRIMARY KEY,
    path_id INTEGER NOT NULL,
    course_id VARCHAR(64),
    title VARCHAR(256),
    order_index INTEGER,
    completed INTEGER
);
CREATE TABLE IF NOT EXISTS user_evaluations (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    subject VARCHAR(64),
    score FLOAT,
    max_score FLOAT,
    notes TEXT,
    evaluated_at DATETIME
);
CREATE TABLE IF NOT EXISTS course_deadlines (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    course_id VARCHAR(64) NOT NULL,
    title VARCHAR(256) NOT NULL,
    deadline DATE NOT NULL
);
"""


def init_orm_course_tables(db_path: str) -> None:
    """Create the ORM(v2)-shaped course tables on a test SQLite file.

    供 ``DbPyCourseProgressRepository(db_path=...)`` 的归一化方法使用
    （生产路径经 ``orm_conn`` 连 xingshi_v2.db，那里由 ORM create_all 建表）。
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_ORM_COURSE_DDL)
        conn.commit()
    finally:
        conn.close()


def init_orm_schema(db_path: str) -> None:
    """Create SQLAlchemy ORM tables for testing.

    Only includes tables that exist in the current User model
    (other slices add tables in later milestones).
    """
    from app.models.base import Base
    from app.models.user import User, StudentProfile

    # M1.2 will add LoginRecord, Profile; M0.4 only needs User and StudentProfile.
    # Defensive optional imports so this module works both before and after M1.2.
    try:
        from app.models.user import LoginRecord  # noqa: F401
    except ImportError:
        pass
    try:
        from app.models.user import Profile  # noqa: F401
    except ImportError:
        pass

    from sqlalchemy import create_engine
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    engine.dispose()


def populate_legacy(db_path: str, users: list = None) -> None:
    """Populate legacy db.py tables with seed data (real user table cols)."""
    users = users or SEED_USERS
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for u in users:
        cur.execute(
            "INSERT OR IGNORE INTO user (id, username, password, preferred_language) VALUES (?, ?, ?, ?)",
            (u["id"], u["username"], u["password"], u["preferred_language"]),
        )
    conn.commit()
    conn.close()


def populate_orm(db_path: str, users: list = None) -> None:
    """Populate ORM tables with seed data.

    Note: ORM users use UUID strings as PK, mapping from int seed IDs.
    """
    users = users or SEED_USERS
    from sqlalchemy import create_engine
    from app.models.base import Base
    from app.models.user import User

    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        for u in users:
            existing = session.query(User).filter_by(username=u["username"]).first()
            if existing:
                continue
            user = User(
                id=f"seed-{u['username']}",
                username=u["username"],
                password_hash=u["password"],
            )
            session.add(user)
        session.commit()
    finally:
        session.close()
    engine.dispose()


def count_users_legacy(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM user")
    n = cur.fetchone()[0]
    conn.close()
    return n


def count_users_orm(db_path: str) -> int:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.user import User

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        return session.query(User).count()
    finally:
        session.close()
