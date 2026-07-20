"""Repository tests for learning-record + evaluation methods (Task A3).

Covers the five methods added to the LearningRepository Protocol and both
implementations:

- ``save_learning_record`` / ``get_learning_record`` — profile snapshot upsert
- ``save_user_evaluation`` — daily metric upsert (merge on same day)
- ``get_user_evaluation`` — single-day read (defaults to today)
- ``get_user_evaluation_history`` — most-recent-N-days read

The ORM path exercises the new ``UserLearningProfile`` and ``UserEvaluationMetric``
models against an in-memory sqlite database. The legacy path delegates to the
``db.py`` helpers against a temp sqlite file (SQL path only, no JSON fallback).
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.learning import UserEvaluationMetric
from app.models.user import User
from app.repositories.legacy.learning import DbPyLearningRepository
from app.repositories.orm.learning import SqlAlchemyLearningRepository


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
def legacy_db(tmp_path, monkeypatch):
    """A legacy sqlite DB with the ``learning_records`` profile-snapshot table.

    ``user_evaluations`` is created on demand by db.py's
    ``_ensure_user_evaluations_table`` helper. ``db.SQLITE_PATH`` is pointed at
    the temp file and the cached backend is forced back to ``sqlite`` so the
    delegating helpers route to our database.
    """
    import db as dbmod

    db_path = str(tmp_path / "legacy_learning.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE learning_records (
            user_id TEXT PRIMARY KEY,
            interaction_count INTEGER DEFAULT 0,
            code_practice_time INTEGER DEFAULT 0,
            socratic_pass_rate REAL DEFAULT 0.0,
            difficulty_level TEXT DEFAULT 'basic',
            profile_json TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(dbmod, "SQLITE_PATH", db_path)
    monkeypatch.setattr(dbmod, "_effective_backend", "sqlite")
    yield db_path


class TestOrmLearningRecord:
    def test_orm_save_and_get_learning_record(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        repo.save_learning_record(
            "u1",
            {
                "interaction_count": 12,
                "code_practice_time": 45,
                "socratic_pass_rate": 0.8,
                "difficulty_level": "intermediate",
                "profile_json": {"topics": ["loops"]},
            },
        )
        orm_session.commit()
        rec = repo.get_learning_record("u1")
        assert rec["interaction_count"] == 12
        assert rec["code_practice_time"] == 45
        assert rec["socratic_pass_rate"] == 0.8
        assert rec["difficulty_level"] == "intermediate"
        assert rec["profile_json"] == {"topics": ["loops"]}

    def test_orm_get_learning_record_no_record_returns_none(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        assert repo.get_learning_record("u1") is None

    def test_orm_save_learning_record_upserts(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        repo.save_learning_record("u1", {"interaction_count": 1})
        orm_session.commit()
        repo.save_learning_record(
            "u1", {"interaction_count": 9, "difficulty_level": "advanced"}
        )
        orm_session.commit()
        from app.models.learning import UserLearningProfile

        assert orm_session.query(UserLearningProfile).count() == 1
        rec = repo.get_learning_record("u1")
        assert rec["interaction_count"] == 9
        assert rec["difficulty_level"] == "advanced"


class TestOrmEvaluation:
    def test_orm_save_user_evaluation_creates_row(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        repo.save_user_evaluation("u1", {"interaction_count": 5})
        orm_session.commit()
        assert len(repo.get_user_evaluation_history("u1")) == 1

    def test_orm_save_user_evaluation_accepts_api_field_names(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        repo.save_user_evaluation(
            "u1",
            {
                "interactionCount": 5,
                "socraticPassRate": 0.8,
                "difficultyLevel": "advanced",
                "codePracticeTime": 30,
                "focusTimeToday": 20,
                "flashcardsStudied": 4,
                "streakDays": 6,
            },
        )
        orm_session.commit()

        rec = repo.get_user_evaluation("u1")

        assert rec["interaction_count"] == 5
        assert rec["socratic_pass_rate"] == 0.8
        assert rec["difficulty_level"] == "advanced"
        assert rec["code_practice_time"] == 30
        assert rec["focus_time_today"] == 20
        assert rec["flashcards_studied"] == 4
        assert rec["streak_days"] == 6

    def test_orm_save_user_evaluation_upserts_same_day(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        repo.save_user_evaluation("u1", {"interaction_count": 5})
        orm_session.commit()
        repo.save_user_evaluation("u1", {"code_practice_time": 30})
        orm_session.commit()
        rows = repo.get_user_evaluation_history("u1")
        assert len(rows) == 1
        # merge semantics: earlier interaction_count preserved
        assert rows[0]["interaction_count"] == 5
        assert rows[0]["code_practice_time"] == 30

    def test_orm_get_user_evaluation_by_date(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        repo.save_user_evaluation("u1", {"interaction_count": 7})
        orm_session.commit()
        rec = repo.get_user_evaluation("u1", date.today().isoformat())
        assert rec is not None
        assert rec["interaction_count"] == 7

    def test_orm_get_user_evaluation_no_date_returns_today(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        repo.save_user_evaluation("u1", {"interaction_count": 3})
        orm_session.commit()
        rec = repo.get_user_evaluation("u1")
        assert rec is not None
        assert rec["interaction_count"] == 3

    def test_orm_get_user_evaluation_no_record_returns_none(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        assert repo.get_user_evaluation("u1") is None

    def test_orm_get_user_evaluation_history_returns_n_days(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        today = date.today()
        for i in range(5):
            orm_session.add(
                UserEvaluationMetric(
                    user_id="u1",
                    interaction_count=i,
                    record_date=today - timedelta(days=i),
                )
            )
        orm_session.commit()
        rows = repo.get_user_evaluation_history("u1", days=3)
        assert len(rows) == 3
        # most-recent first
        assert rows[0]["record_date"] == today.isoformat()

    def test_orm_get_user_evaluation_history_default_days(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        today = date.today()
        for i in range(10):
            orm_session.add(
                UserEvaluationMetric(
                    user_id="u1",
                    interaction_count=i,
                    record_date=today - timedelta(days=i),
                )
            )
        orm_session.commit()
        assert len(repo.get_user_evaluation_history("u1")) == 7


class TestLegacyLearningRecord:
    def test_legacy_save_and_get_learning_record(self, legacy_db):
        repo = DbPyLearningRepository(legacy_db)
        repo.save_learning_record(
            "1",
            {
                "interaction_count": 4,
                "code_practice_time": 20,
                "socratic_pass_rate": 0.5,
                "difficulty_level": "basic",
                "profile_json": "{}",
            },
        )
        rec = repo.get_learning_record("1")
        assert rec["interaction_count"] == 4
        assert rec["code_practice_time"] == 20
        assert rec["difficulty_level"] == "basic"

    def test_legacy_get_learning_record_no_record_returns_none(self, legacy_db):
        repo = DbPyLearningRepository(legacy_db)
        assert repo.get_learning_record("999") is None


class TestLegacyEvaluation:
    def test_legacy_save_user_evaluation(self, legacy_db):
        repo = DbPyLearningRepository(legacy_db)
        repo.save_user_evaluation("1", {"interactionCount": 6})
        rows = repo.get_user_evaluation_history("1")
        assert len(rows) == 1
        assert rows[0]["interaction_count"] == 6

    def test_legacy_get_user_evaluation_by_date(self, legacy_db):
        repo = DbPyLearningRepository(legacy_db)
        repo.save_user_evaluation("1", {"interactionCount": 8})
        rec = repo.get_user_evaluation("1", date.today().isoformat())
        assert rec is not None
        assert rec["interaction_count"] == 8

    def test_legacy_get_user_evaluation_history(self, legacy_db):
        repo = DbPyLearningRepository(legacy_db)
        repo.save_user_evaluation("1", {"interactionCount": 2})
        rows = repo.get_user_evaluation_history("1", days=7)
        assert isinstance(rows, list)
        assert len(rows) == 1


class TestProtocolCompliance:
    def test_protocol_includes_new_methods(self):
        from app.repositories.base import LearningRepository

        proto = LearningRepository.__dict__
        for m in (
            "save_learning_record",
            "get_learning_record",
            "save_user_evaluation",
            "get_user_evaluation",
            "get_user_evaluation_history",
        ):
            assert m in proto, f"Protocol missing method: {m}"

    def test_orm_implements_new_methods(self):
        repo = SqlAlchemyLearningRepository.__dict__
        for m in (
            "save_learning_record",
            "get_learning_record",
            "save_user_evaluation",
            "get_user_evaluation",
            "get_user_evaluation_history",
        ):
            assert m in repo, f"ORM repo missing method: {m}"

    def test_legacy_implements_new_methods(self):
        repo = DbPyLearningRepository.__dict__
        for m in (
            "save_learning_record",
            "get_learning_record",
            "save_user_evaluation",
            "get_user_evaluation",
            "get_user_evaluation_history",
        ):
            assert m in repo, f"legacy repo missing method: {m}"
