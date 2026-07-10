"""Seed data generators for dual-backend testing.

Provides consistent data across legacy db.py schema and ORM schema.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json


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
    """Create db.py-style tables for testing."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # db.py 'user' table (INT PK)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(128) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            preferred_language VARCHAR(16) DEFAULT 'zh-CN'
        )
    """)

    # db.py 'user_profile' table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            user_id INTEGER PRIMARY KEY,
            preferred_language VARCHAR(16),
            theme VARCHAR(32)
        )
    """)

    # db.py 'user_login_records' table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_login_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ip VARCHAR(64),
            user_agent VARCHAR(512),
            login_at TEXT
        )
    """)

    # db.py 'user_preferences' table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id INTEGER NOT NULL,
            key VARCHAR(128) NOT NULL,
            value TEXT,
            updated_at TEXT,
            PRIMARY KEY (user_id, key)
        )
    """)

    # M2: legacy schema additions for settings + theme KV mirrors
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            setting_key VARCHAR(128) NOT NULL,
            setting_value TEXT,
            updated_at TEXT,
            UNIQUE(user_id, setting_key)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_themes (
            user_id INTEGER PRIMARY KEY,
            theme VARCHAR(32) DEFAULT 'dark',
            accent_color VARCHAR(16) DEFAULT '#7c3aed',
            updated_at TEXT
        )
    """)

    # M3: legacy schema additions for learning statistics
    cur.execute("""
        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject VARCHAR(64),
            duration_minutes INTEGER DEFAULT 0,
            session_date TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS learning_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_type VARCHAR(64) DEFAULT 'study',
            subject VARCHAR(64),
            minutes INTEGER DEFAULT 0,
            metadata TEXT,
            recorded_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id INTEGER PRIMARY KEY,
            total_minutes INTEGER DEFAULT 0,
            streak_days INTEGER DEFAULT 0,
            completed_courses INTEGER DEFAULT 0,
            last_active TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS learning_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title VARCHAR(256),
            target_value REAL DEFAULT 0,
            current_value REAL DEFAULT 0,
            unit VARCHAR(32) DEFAULT 'minutes',
            deadline TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS weekly_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week_start TEXT,
            total_minutes INTEGER DEFAULT 0,
            subjects TEXT
        )
    """)

    # M5: legacy schema additions for course progress + learning paths
    cur.execute("""
        CREATE TABLE IF NOT EXISTS course_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id VARCHAR(64) NOT NULL,
            progress_percent REAL DEFAULT 0,
            completed_at TEXT,
            last_accessed TEXT,
            state TEXT,
            UNIQUE(user_id, course_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS learning_paths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name VARCHAR(256),
            description TEXT,
            status VARCHAR(32) DEFAULT 'active',
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS learning_path_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path_id INTEGER NOT NULL,
            course_id VARCHAR(64),
            title VARCHAR(256),
            order_index INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject VARCHAR(64),
            score REAL DEFAULT 0,
            max_score REAL DEFAULT 100,
            notes TEXT,
            evaluated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS course_generation_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id VARCHAR(64) NOT NULL,
            status VARCHAR(32) DEFAULT 'pending',
            progress_percent REAL DEFAULT 0,
            error_message TEXT,
            started_at TEXT,
            completed_at TEXT
        )
    """)

    # M6: legacy schema additions for knowledge graph + SM2 reviews
    cur.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name VARCHAR(256) NOT NULL,
            subject VARCHAR(64),
            description TEXT,
            mastery REAL DEFAULT 0,
            importance INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            source_node_id INTEGER NOT NULL,
            target_node_id INTEGER NOT NULL,
            relation_type VARCHAR(64) DEFAULT 'related',
            weight REAL DEFAULT 1.0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            node_id INTEGER NOT NULL,
            ease_factor REAL DEFAULT 2.5,
            interval_days INTEGER DEFAULT 1,
            repetitions INTEGER DEFAULT 0,
            next_review_date TEXT,
            last_reviewed_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            node_id INTEGER NOT NULL,
            action VARCHAR(64) DEFAULT 'view',
            quality INTEGER DEFAULT 0,
            notes TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_pending (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            node_id INTEGER NOT NULL,
            due_date TEXT,
            priority INTEGER DEFAULT 0
        )
    """)

    # M7: legacy schema additions for focus session tracking
    cur.execute("""
        CREATE TABLE IF NOT EXISTS focus_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            started_at TEXT,
            ended_at TEXT,
            duration_minutes INTEGER DEFAULT 0,
            planned_minutes INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            subject VARCHAR(64)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS focus_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            event_type VARCHAR(64) DEFAULT 'start',
            timestamp TEXT,
            flow_score REAL DEFAULT 0,
            metadata TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_focus_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            focus_date TEXT,
            total_focus_minutes INTEGER DEFAULT 0,
            sessions_count INTEGER DEFAULT 0,
            avg_flow_score REAL DEFAULT 0,
            deep_focus_minutes INTEGER DEFAULT 0
        )
    """)

    conn.commit()
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
    """Populate legacy db.py tables with seed data."""
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
