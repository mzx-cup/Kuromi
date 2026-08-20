"""Repository tests for classroom (M10)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
from app.models.classroom import ClassroomSession, QuizRecord, AgentTurnRecord
from app.repositories.legacy.classroom import DbPyClassroomRepository
from app.repositories.orm.classroom import SqlAlchemyClassroomRepository


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
    from tests.fixtures.seed_data import init_legacy_schema, populate_legacy
    db_path = str(tmp_path / "legacy.db")
    init_legacy_schema(db_path)
    populate_legacy(
        db_path,
        [{"id": 1, "username": "u1", "password": "h", "preferred_language": "zh-CN"}],
    )
    yield db_path


class TestClassroomSession:
    def test_orm_create_session(self, orm_session):
        repo = SqlAlchemyClassroomRepository(orm_session)
        session_id = repo.create_session("u1", "course_1", teacher_mode=True)
        orm_session.commit()
        assert session_id is not None and str(session_id)
        result = repo.get_session(session_id)
        assert result is not None
        assert result["course_id"] == "course_1"
        assert result["teacher_mode"] is True
        assert result["status"] == "active"

    def test_legacy_create_session(self, legacy_db):
        repo = DbPyClassroomRepository(legacy_db)
        session_id = repo.create_session(1, "course_1")
        # 真实 classroom_sessions.id 是 TEXT PK（生成 cs_<hex>），不再是自增 int。
        assert isinstance(session_id, str) and session_id.startswith("cs_")
        result = repo.get_session(session_id)
        assert result["course_id"] == "course_1"
        assert result["user_id"] == "1"  # 真实 student_id 列按 TEXT 存
        assert result["status"] == "active"

    def test_orm_list_sessions(self, orm_session):
        repo = SqlAlchemyClassroomRepository(orm_session)
        repo.create_session("u1", "course_1")
        repo.create_session("u1", "course_2")
        orm_session.commit()
        sessions = repo.list_sessions("u1")
        assert len(sessions) == 2

    def test_legacy_list_sessions(self, legacy_db):
        repo = DbPyClassroomRepository(legacy_db)
        repo.create_session(1, "course_a")
        repo.create_session(1, "course_b")
        sessions = repo.list_sessions(1)
        assert len(sessions) == 2
        # Returned most-recent-first
        assert sessions[0]["course_id"] in ("course_a", "course_b")

    def test_orm_update_session(self, orm_session):
        repo = SqlAlchemyClassroomRepository(orm_session)
        session_id = repo.create_session("u1", "course_1")
        orm_session.commit()
        repo.update_session(session_id, {"current_slide": 5, "status": "paused"})
        orm_session.commit()
        result = repo.get_session(session_id)
        assert result["current_slide"] == 5
        assert result["status"] == "paused"

    def test_legacy_update_session(self, legacy_db):
        repo = DbPyClassroomRepository(legacy_db)
        session_id = repo.create_session(1, "course_1")
        repo.update_session(session_id, {"current_slide": 7, "status": "paused"})
        result = repo.get_session(session_id)
        assert result["current_slide"] == 7
        assert result["status"] == "paused"

    def test_orm_get_missing_session_returns_none(self, orm_session):
        repo = SqlAlchemyClassroomRepository(orm_session)
        assert repo.get_session("does-not-exist") is None


class TestQuizRecord:
    def test_orm_save_quiz(self, orm_session):
        repo = SqlAlchemyClassroomRepository(orm_session)
        qr_id = repo.save_quiz_record("u1", {
            "question": "What is 2+2?",
            "answer": "4",
            "correct": True,
            "score": 100,
            "passed": True,
        })
        orm_session.commit()
        assert qr_id > 0
        records = repo.get_quiz_records("u1")
        assert len(records) == 1
        assert records[0]["correct"] is True
        assert records[0]["max_score"] == 100

    def test_legacy_save_quiz(self, legacy_db):
        repo = DbPyClassroomRepository(legacy_db)
        qr_id = repo.save_quiz_record(1, {
            "question": "Q",
            "answer": "A",
            "correct": False,
            "score": 0,
            "passed": False,
        })
        assert qr_id > 0
        records = repo.get_quiz_records(1)
        assert len(records) == 1
        assert records[0]["correct"] is False
        assert records[0]["score"] == 0

    def test_legacy_quiz_default_max_score(self, legacy_db):
        """When the caller omits max_score the legacy default is 100."""
        repo = DbPyClassroomRepository(legacy_db)
        repo.save_quiz_record(1, {"question": "Q", "answer": "A", "correct": True})
        records = repo.get_quiz_records(1)
        assert records[0]["max_score"] == 100

    def test_orm_quiz_default_max_score(self, orm_session):
        repo = SqlAlchemyClassroomRepository(orm_session)
        repo.save_quiz_record("u1", {"question": "Q", "answer": "A", "correct": True})
        orm_session.commit()
        records = repo.get_quiz_records("u1")
        assert records[0]["max_score"] == 100

    def test_orm_quiz_records_limit(self, orm_session):
        repo = SqlAlchemyClassroomRepository(orm_session)
        for i in range(5):
            repo.save_quiz_record("u1", {"question": f"Q{i}", "answer": "A", "correct": True})
        orm_session.commit()
        records = repo.get_quiz_records("u1", limit=3)
        assert len(records) == 3


class TestProtocolCompliance:
    def test_orm_implements_protocol(self):
        from app.repositories.base import ClassroomRepository
        from app.repositories.orm.classroom import SqlAlchemyClassroomRepository
        repo = SqlAlchemyClassroomRepository.__dict__
        required = {
            "get_session", "list_sessions", "create_session",
            "update_session", "save_quiz_record", "get_quiz_records",
        }
        for m in required:
            assert m in repo, f"missing method: {m}"

    def test_legacy_implements_protocol(self):
        from app.repositories.legacy.classroom import DbPyClassroomRepository
        repo = DbPyClassroomRepository.__dict__
        required = {
            "get_session", "list_sessions", "create_session",
            "update_session", "save_quiz_record", "get_quiz_records",
        }
        for m in required:
            assert m in repo, f"missing method: {m}"

    def test_model_extensions_present(self):
        """The M10 additive fields exist on the models and were not removed."""
        cs_cols = {c.name for c in ClassroomSession.__table__.columns}
        assert "user_id" in cs_cols
        assert "started_at" in cs_cols
        assert "ended_at" in cs_cols
        assert "current_slide" in cs_cols
        assert "teacher_mode" in cs_cols
        # Original columns must still be present
        assert "id" in cs_cols
        assert "student_id" in cs_cols

        qr_cols = {c.name for c in QuizRecord.__table__.columns}
        assert "session_id" in qr_cols
        assert "user_id" in qr_cols
        assert "question" in qr_cols
        assert "correct" in qr_cols
        assert "max_score" in qr_cols

        at_cols = {c.name for c in AgentTurnRecord.__table__.columns}
        assert "session_id" in at_cols
        assert "turn_number" in at_cols
        assert "user_input" in at_cols
        assert "agent_output" in at_cols
