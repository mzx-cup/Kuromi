"""Repository unit tests for course progress (M5)."""
import json
import sqlite3

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.course_progress import (
    CourseProgress,
    LearningPath,
    LearningPathNode,
    UserEvaluation,
)
from app.models.user import User
from app.repositories.legacy.course_progress import (
    DbPyCourseProgressRepository,
)
from app.repositories.orm.course_progress import (
    SqlAlchemyCourseProgressRepository,
)


@pytest.fixture
def orm_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        session.add(User(id="u1", username="u1", password_hash="h"))
        session.commit()
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def legacy_db(tmp_path):
    from tests.fixtures.seed_data import init_legacy_schema, populate_legacy

    db_path = str(tmp_path / "legacy.db")
    init_legacy_schema(db_path)
    populate_legacy(
        db_path,
        [
            {"id": 1, "username": "u1", "password": "h", "preferred_language": "zh-CN"},
        ],
    )
    yield db_path


# ── CourseProgress ──


class TestCourseProgressOrm:
    def test_save_and_get(self, orm_session):
        repo = SqlAlchemyCourseProgressRepository(orm_session)
        repo.save_progress("u1", "course_1", 50.0, {"chapter": 3})
        orm_session.commit()
        result = repo.get_progress("u1", "course_1")
        assert result is not None
        assert result["progress_percent"] == 50.0
        assert result["state"]["chapter"] == 3

    def test_get_nonexistent(self, orm_session):
        repo = SqlAlchemyCourseProgressRepository(orm_session)
        assert repo.get_progress("u1", "missing") is None

    def test_save_updates_existing(self, orm_session):
        repo = SqlAlchemyCourseProgressRepository(orm_session)
        repo.save_progress("u1", "course_1", 25.0, {"chapter": 1})
        orm_session.commit()
        repo.save_progress("u1", "course_1", 75.0, {"chapter": 5})
        orm_session.commit()
        result = repo.get_progress("u1", "course_1")
        assert result["progress_percent"] == 75.0
        assert result["state"]["chapter"] == 5


class TestCourseProgressLegacy:
    def test_save_and_get(self, legacy_db):
        repo = DbPyCourseProgressRepository(legacy_db)
        repo.save_progress(1, "course_1", 75.0, {"chapter": 5})
        result = repo.get_progress(1, "course_1")
        assert result is not None
        assert result["progress_percent"] == 75.0
        assert result["state"]["chapter"] == 5

    def test_get_nonexistent(self, legacy_db):
        repo = DbPyCourseProgressRepository(legacy_db)
        assert repo.get_progress(1, "missing") is None

    def test_save_updates_existing(self, legacy_db):
        repo = DbPyCourseProgressRepository(legacy_db)
        repo.save_progress(1, "course_1", 25.0, {"chapter": 1})
        repo.save_progress(1, "course_1", 75.0, {"chapter": 5})
        result = repo.get_progress(1, "course_1")
        assert result["progress_percent"] == 75.0
        assert result["state"]["chapter"] == 5


# ── LearningPath ──


class TestLearningPathOrm:
    def test_get_empty(self, orm_session):
        repo = SqlAlchemyCourseProgressRepository(orm_session)
        assert repo.get_learning_path("u1") == []

    def test_get_with_nodes(self, orm_session):
        path = LearningPath(user_id="u1", name="Path A", description="desc")
        orm_session.add(path)
        orm_session.flush()
        orm_session.add(LearningPathNode(path_id=path.id, course_id="c1", title="C1", order_index=0))
        orm_session.add(LearningPathNode(path_id=path.id, course_id="c2", title="C2", order_index=1, completed=True))
        orm_session.commit()

        repo = SqlAlchemyCourseProgressRepository(orm_session)
        result = repo.get_learning_path("u1")
        assert len(result) == 1
        assert result[0]["name"] == "Path A"
        assert len(result[0]["nodes"]) == 2
        assert result[0]["nodes"][1]["completed"] is True


class TestLearningPathLegacy:
    def test_get_empty(self, legacy_db):
        repo = DbPyCourseProgressRepository(legacy_db)
        assert repo.get_learning_path(1) == []

    def test_get_with_nodes(self, legacy_db):
        conn = sqlite3.connect(legacy_db)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO learning_paths (user_id, name, description, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (1, "Path A", "desc", "active", "2024-01-01T00:00:00"),
        )
        path_id = cur.lastrowid
        cur.execute(
            "INSERT INTO learning_path_nodes (path_id, course_id, title, order_index, completed) VALUES (?, ?, ?, ?, ?)",
            (path_id, "c1", "C1", 0, 0),
        )
        cur.execute(
            "INSERT INTO learning_path_nodes (path_id, course_id, title, order_index, completed) VALUES (?, ?, ?, ?, ?)",
            (path_id, "c2", "C2", 1, 1),
        )
        conn.commit()
        conn.close()

        repo = DbPyCourseProgressRepository(legacy_db)
        result = repo.get_learning_path(1)
        assert len(result) == 1
        assert result[0]["name"] == "Path A"
        assert len(result[0]["nodes"]) == 2
        assert result[0]["nodes"][1]["completed"] is True


# ── UserEvaluation ──


class TestEvaluationsOrm:
    def test_get_empty(self, orm_session):
        repo = SqlAlchemyCourseProgressRepository(orm_session)
        assert repo.get_evaluations("u1") == []

    def test_get_with_rows(self, orm_session):
        orm_session.add(UserEvaluation(user_id="u1", subject="math", score=85.0, max_score=100.0, notes="ok"))
        orm_session.commit()
        repo = SqlAlchemyCourseProgressRepository(orm_session)
        result = repo.get_evaluations("u1")
        assert len(result) == 1
        assert result[0]["subject"] == "math"
        assert result[0]["score"] == 85.0


class TestEvaluationsLegacy:
    def test_get_empty(self, legacy_db):
        repo = DbPyCourseProgressRepository(legacy_db)
        assert repo.get_evaluations(1) == []

    def test_get_with_rows(self, legacy_db):
        conn = sqlite3.connect(legacy_db)
        conn.execute(
            "INSERT INTO user_evaluations (user_id, subject, score, max_score, notes, evaluated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (1, "math", 85.0, 100.0, "ok", "2024-01-01T00:00:00"),
        )
        conn.commit()
        conn.close()
        repo = DbPyCourseProgressRepository(legacy_db)
        result = repo.get_evaluations(1)
        assert len(result) == 1
        assert result[0]["subject"] == "math"
        assert result[0]["score"] == 85.0


# ── Symmetry: legacy & ORM produce equivalent shapes when seeded equivalently ──


class TestSymmetry:
    def test_progress_shape_matches(self, orm_session, legacy_db):
        orm_repo = SqlAlchemyCourseProgressRepository(orm_session)
        orm_repo.save_progress("u1", "course_1", 42.0, {"k": "v"})
        orm_session.commit()
        legacy_repo = DbPyCourseProgressRepository(legacy_db)
        legacy_repo.save_progress(1, "course_1", 42.0, {"k": "v"})

        o = orm_repo.get_progress("u1", "course_1")
        l = legacy_repo.get_progress(1, "course_1")
        assert set(o.keys()) == set(l.keys())
        assert o["state"] == l["state"]
        assert o["progress_percent"] == l["progress_percent"]
