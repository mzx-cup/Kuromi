"""Repository unit tests for learning statistics write path (M4)."""
import sqlite3

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.learning import LearningGoal
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
        user = User(id="u1", username="u1", password_hash="h")
        session.add(user)
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


class TestRecordSession:
    def test_orm_record_session(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        repo.record_session(
            "u1",
            {
                "subject": "math",
                "minutes": 45,
                "activity_type": "study",
                "metadata": {"source": "test"},
            },
        )
        orm_session.commit()
        result = repo.get_overview("u1")
        assert result["total_minutes"] == 45
        assert result["study_days"] == 1

    def test_orm_record_session_uses_duration_minutes(self, orm_session):
        """When only 'duration_minutes' is provided, fall back to that key."""
        repo = SqlAlchemyLearningRepository(orm_session)
        repo.record_session(
            "u1",
            {
                "subject": "english",
                "duration_minutes": 25,
                "activity_type": "study",
            },
        )
        orm_session.commit()
        result = repo.get_overview("u1")
        assert result["total_minutes"] == 25

    def test_orm_record_session_invalid_date_falls_back_to_today(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        repo.record_session(
            "u1",
            {
                "subject": "math",
                "minutes": 10,
                "session_date": "not-a-date",
            },
        )
        orm_session.commit()
        result = repo.get_overview("u1")
        assert result["total_minutes"] == 10

    def test_legacy_record_session(self, legacy_db):
        repo = DbPyLearningRepository(legacy_db)
        repo.record_session(
            1,
            {
                "subject": "math",
                "minutes": 30,
                "activity_type": "study",
            },
        )
        result = repo.get_overview(1)
        assert result["total_minutes"] == 30
        assert result["study_days"] == 1

    def test_legacy_record_session_creates_learning_record(self, legacy_db):
        """Verify a learning_records row was also inserted (for mastery)."""
        repo = DbPyLearningRepository(legacy_db)
        repo.record_session(
            1,
            {
                "subject": "physics",
                "minutes": 20,
                "activity_type": "practice",
            },
        )
        conn = sqlite3.connect(legacy_db)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM learning_records WHERE user_id = ? AND subject = ?",
            (1, "physics"),
        )
        n = cur.fetchone()[0]
        conn.close()
        assert n == 1


class TestGoals:
    def test_orm_create_goal(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        goal_id = repo.record_goal(
            "u1",
            {
                "title": "数学冲刺",
                "target_value": 80,
                "current_value": 0,
                "unit": "minutes",
            },
        )
        assert isinstance(goal_id, int)
        assert goal_id > 0
        orm_session.commit()

    def test_orm_update_goal(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        goal_id = repo.record_goal("u1", {"title": "Test", "target_value": 10})
        orm_session.commit()
        new_id = repo.record_goal(
            "u1", {"id": goal_id, "title": "Updated", "target_value": 20}
        )
        assert new_id == goal_id
        # Verify the row was actually mutated
        updated = orm_session.query(LearningGoal).filter_by(id=goal_id).first()
        assert updated is not None
        assert updated.title == "Updated"
        assert updated.target_value == 20

    def test_orm_delete_goal(self, orm_session):
        repo = SqlAlchemyLearningRepository(orm_session)
        goal_id = repo.record_goal("u1", {"title": "Test", "target_value": 10})
        orm_session.commit()
        repo.delete_goal("u1", goal_id)
        orm_session.commit()
        # Verify the row was deleted
        goal = orm_session.query(LearningGoal).filter_by(id=goal_id).first()
        assert goal is None

    def test_orm_delete_goal_missing_user_id_no_op(self, orm_session):
        """delete_goal should silently skip when goal belongs to another user."""
        repo = SqlAlchemyLearningRepository(orm_session)
        goal_id = repo.record_goal("u1", {"title": "Test", "target_value": 10})
        orm_session.commit()
        # Different user_id: should not raise
        repo.delete_goal("other_user", goal_id)
        orm_session.commit()
        # Goal still exists for the original user
        goal = orm_session.query(LearningGoal).filter_by(id=goal_id).first()
        assert goal is not None

    def test_legacy_create_goal(self, legacy_db):
        repo = DbPyLearningRepository(legacy_db)
        goal_id = repo.record_goal(1, {"title": "Test", "target_value": 10})
        assert isinstance(goal_id, int)
        assert goal_id > 0

    def test_legacy_update_goal_returns_same_id(self, legacy_db):
        repo = DbPyLearningRepository(legacy_db)
        goal_id = repo.record_goal(1, {"title": "Test", "target_value": 10})
        same_id = repo.record_goal(
            1, {"id": goal_id, "title": "Updated", "target_value": 20}
        )
        assert same_id == goal_id

    def test_legacy_delete_goal(self, legacy_db):
        repo = DbPyLearningRepository(legacy_db)
        goal_id = repo.record_goal(1, {"title": "Test", "target_value": 10})
        repo.delete_goal(1, goal_id)
        # Verify deletion
        conn = sqlite3.connect(legacy_db)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM learning_goals WHERE id = ?", (goal_id,))
        n = cur.fetchone()[0]
        conn.close()
        assert n == 0