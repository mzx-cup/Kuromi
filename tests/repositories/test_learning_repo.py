"""Repository unit tests for learning statistics (M3 read path)."""
import sqlite3
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.learning import LearningRecord, StudySession
from app.models.user import User
from app.repositories.legacy.learning import DbPyLearningRepository
from app.repositories.orm.learning import SqlAlchemyLearningRepository


@pytest.fixture
def orm_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        # Seed a user
        user = User(id="u1", username="u1", password_hash="h")
        session.add(user)
        # Seed study sessions
        today = datetime.now().date()
        for i in range(3):
            s = StudySession(
                user_id="u1",
                subject="math",
                duration_minutes=30,
                session_date=today - timedelta(days=i),
            )
            session.add(s)
        # Seed learning records for mastery
        for i in range(2):
            r = LearningRecord(
                user_id="u1",
                subject="math",
                activity_type="practice",
                minutes=10,
            )
            session.add(r)
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

    conn = sqlite3.connect(db_path)
    today = datetime.now().date()
    for i in range(3):
        conn.execute(
            "INSERT INTO study_sessions (user_id, subject, duration_minutes, session_date) VALUES (?, ?, ?, ?)",
            (1, "math", 30, str(today - timedelta(days=i))),
        )
    conn.execute(
        "INSERT INTO learning_records (user_id, activity_type, subject, minutes) VALUES (?, ?, ?, ?)",
        (1, "practice", "math", 10),
    )
    conn.execute(
        "INSERT INTO learning_records (user_id, activity_type, subject, minutes) VALUES (?, ?, ?, ?)",
        (1, "practice", "math", 20),
    )
    conn.commit()
    conn.close()
    yield db_path


class TestSqlAlchemyLearningRepository:
    def test_get_overview(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        result = repo.get_overview("u1")
        assert result["total_minutes"] == 90
        assert result["study_days"] == 3
        assert result["current_streak"] >= 1

    def test_get_trend(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        result = repo.get_trend("u1", 7)
        assert isinstance(result, list)
        assert len(result) >= 1
        # Each entry has date/minutes
        assert "date" in result[0]
        assert "minutes" in result[0]

    def test_get_heatmap(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        result = repo.get_heatmap("u1")
        assert isinstance(result, dict)
        assert len(result) >= 1

    def test_get_mastery(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        result = repo.get_mastery("u1")
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "subject" in result[0]
        assert "topic" in result[0]
        assert "mastery" in result[0]

    def test_get_overview_empty_user(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        result = repo.get_overview("ghost")
        assert result["total_minutes"] == 0
        assert result["study_days"] == 0
        assert result["current_streak"] == 0


class TestDbPyLearningRepository:
    def test_get_overview(self, legacy_db):
        repo = DbPyLearningRepository(legacy_db)
        result = repo.get_overview(1)
        assert result["total_minutes"] == 90
        assert result["study_days"] == 3
        assert result["current_streak"] >= 1

    def test_get_trend(self, legacy_db):
        repo = DbPyLearningRepository(legacy_db)
        result = repo.get_trend(1, 7)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_get_heatmap(self, legacy_db):
        repo = DbPyLearningRepository(legacy_db)
        result = repo.get_heatmap(1)
        assert isinstance(result, dict)
        assert len(result) >= 1

    def test_get_mastery(self, legacy_db):
        repo = DbPyLearningRepository(legacy_db)
        result = repo.get_mastery(1)
        assert isinstance(result, list)
        assert len(result) >= 1
