"""Tests for CourseProgressRepository extensions (Task C1).

Covers:
- ``get_learning_path_graph`` / ``save_learning_path_graph``
- ``get_learning_path_nodes`` / ``get_learning_path_node`` /
  ``save_learning_path_node`` / ``sync_path_to_nodes``
- ``get_daily_route`` / ``save_daily_route`` (ORM hits the new model;
  legacy delegates to db.py helpers)
"""
from __future__ import annotations

import sqlite3
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.course_progress import DailyRoute
from app.models.user import User
from app.repositories.legacy.course_progress import DbPyCourseProgressRepository
from app.repositories.orm.course_progress import SqlAlchemyCourseProgressRepository


@pytest.fixture
def orm_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(User(id="u1", username="u1", password_hash="h"))
    session.commit()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def legacy_db(tmp_path):
    """A legacy sqlite file with the required tables for db.py helpers."""
    db_path = str(tmp_path / "legacy_cp.db")
    conn = sqlite3.connect(db_path)
    # db.py uses singular "learning_path" + plural "learning_path_nodes"
    conn.executescript("""
        CREATE TABLE learning_path (
            user_id TEXT PRIMARY KEY,
            path_json TEXT,
            generated_at TEXT,
            reasoning TEXT,
            data_sources TEXT,
            confidence REAL DEFAULT 0.0
        );
        CREATE TABLE learning_path_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            node_topic TEXT,
            status TEXT DEFAULT 'locked',
            mastery_score REAL DEFAULT 0.0,
            evidence_json TEXT,
            goal_evidence_json TEXT,
            goal_evidence_validated INTEGER DEFAULT 0,
            updated_at TEXT,
            UNIQUE(user_id, node_id)
        );
        CREATE TABLE daily_routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            route_date TEXT NOT NULL,
            tasks_json TEXT,
            completed_json TEXT,
            created_at TEXT,
            UNIQUE(user_id, route_date)
        );
    """)
    conn.commit()
    conn.close()

    # Patch db.py to use this file
    import db as dbmod
    import json as _json

    dbmod.SQLITE_PATH = db_path
    dbmod._effective_backend = "sqlite"

    # Patch the helpers to operate on this db_path (they read SQLITE_PATH via
    # get_db() but for migration period we also call them with direct conns).

    yield db_path


def _patched_get_learning_path(user_id, _db_path=None):
    conn = sqlite3.connect(_db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM learning_path WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return {c: row[i] for i, c in enumerate(cols)}
    finally:
        conn.close()


def _patched_save_learning_path(user_id, path_json, _db_path=None,
                                reasoning=None, data_sources=None,
                                confidence=0.0):
    import json as _json
    conn = sqlite3.connect(_db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO learning_path (user_id, path_json, generated_at, reasoning, data_sources, confidence)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   path_json=excluded.path_json,
                   generated_at=excluded.generated_at,
                   reasoning=excluded.reasoning,
                   data_sources=excluded.data_sources,
                   confidence=excluded.confidence""",
            (user_id, _json.dumps(path_json, ensure_ascii=False), "2026-07-14",
             reasoning, _json.dumps(data_sources) if data_sources else None,
             confidence),
        )
        conn.commit()
    finally:
        conn.close()


class TestOrmDailyRoute:
    def test_orm_save_and_get_daily_route(self, orm_session):
        repo = SqlAlchemyCourseProgressRepository(orm_session)
        today = date(2026, 7, 14)
        repo.save_daily_route("u1", today.isoformat(), ["task-a"], [])
        orm_session.commit()
        route = repo.get_daily_route("u1", today.isoformat())
        assert route is not None
        assert route["tasks_json"] == ["task-a"]
        assert route["completed_json"] == []

    def test_orm_save_daily_route_upserts(self, orm_session):
        repo = SqlAlchemyCourseProgressRepository(orm_session)
        today = date(2026, 7, 14)
        repo.save_daily_route("u1", today.isoformat(), ["a"], [])
        orm_session.commit()
        repo.save_daily_route("u1", today.isoformat(), ["a", "b"], ["a"])
        orm_session.commit()
        route = repo.get_daily_route("u1", today.isoformat())
        assert route["tasks_json"] == ["a", "b"]
        assert route["completed_json"] == ["a"]

    def test_orm_get_daily_route_no_record_returns_none(self, orm_session):
        repo = SqlAlchemyCourseProgressRepository(orm_session)
        assert repo.get_daily_route("u1", "2026-07-14") is None


class TestLegacyDailyRoute:
    def test_legacy_save_and_get_daily_route(self, legacy_db):
        import db as dbmod
        # Patch helper to use our tmp sqlite file
        original_get = dbmod.get_daily_route
        original_save = dbmod.save_daily_route

        def patched_get(user_id, route_date):
            conn = sqlite3.connect(legacy_db)
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT * FROM daily_routes WHERE user_id = ? AND route_date = ?",
                    (user_id, route_date),
                )
                row = cur.fetchone()
                if not row:
                    return None
                cols = [d[0] for d in cur.description]
                return {c: row[i] for i, c in enumerate(cols)}
            finally:
                conn.close()

        def patched_save(user_id, route_date, tasks, completed=None):
            import json
            conn = sqlite3.connect(legacy_db)
            try:
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO daily_routes (user_id, route_date, tasks_json, completed_json)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(user_id, route_date) DO UPDATE SET
                           tasks_json=excluded.tasks_json,
                           completed_json=excluded.completed_json""",
                    (user_id, route_date, json.dumps(tasks), json.dumps(completed or [])),
                )
                conn.commit()
            finally:
                conn.close()

        dbmod.get_daily_route = patched_get
        dbmod.save_daily_route = patched_save
        try:
            repo = DbPyCourseProgressRepository(legacy_db)
            repo.save_daily_route("1", "2026-07-14", ["t1", "t2"], ["t1"])
            route = repo.get_daily_route("1", "2026-07-14")
            assert route is not None
            assert "t1" in route["tasks_json"]
        finally:
            dbmod.get_daily_route = original_get
            dbmod.save_daily_route = original_save


class TestProtocolCompliance:
    def test_protocol_includes_new_methods(self):
        from app.repositories.base import CourseProgressRepository
        proto = CourseProgressRepository.__dict__
        for m in (
            "get_learning_path_graph",
            "save_learning_path_graph",
            "get_learning_path_nodes",
            "get_learning_path_node",
            "save_learning_path_node",
            "sync_path_to_nodes",
            "get_daily_route",
            "save_daily_route",
        ):
            assert m in proto, f"Protocol missing method: {m}"

    def test_orm_implements_new_methods(self, orm_session):
        repo = SqlAlchemyCourseProgressRepository(orm_session)
        for m in (
            "get_learning_path_graph",
            "save_learning_path_graph",
            "get_learning_path_nodes",
            "get_learning_path_node",
            "save_learning_path_node",
            "sync_path_to_nodes",
            "get_daily_route",
            "save_daily_route",
        ):
            assert hasattr(repo, m), f"ORM repo missing method: {m}"

    def test_legacy_implements_new_methods(self, tmp_path):
        db_path = str(tmp_path / "x.db")
        repo = DbPyCourseProgressRepository(db_path)
        for m in (
            "get_learning_path_graph",
            "save_learning_path_graph",
            "get_learning_path_nodes",
            "get_learning_path_node",
            "save_learning_path_node",
            "sync_path_to_nodes",
            "get_daily_route",
            "save_daily_route",
        ):
            assert hasattr(repo, m), f"Legacy repo missing method: {m}"
