"""Repository tests for focus session tracking (M7)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
from app.repositories.legacy.focus import DbPyFocusRepository
from app.repositories.orm.focus import SqlAlchemyFocusRepository


@pytest.fixture
def orm_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
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


class TestFocusSession:
    def test_orm_start_and_end_session(self, orm_session):
        repo = SqlAlchemyFocusRepository(orm_session)
        session_id = repo.start_session("u1", 25, "math")
        assert session_id > 0
        repo.end_session(session_id, 25, completed=True)
        orm_session.commit()
        events = repo.get_events(session_id)
        # No events added in this test, but session should exist
        assert isinstance(events, list)

    def test_legacy_start_and_end_session(self, legacy_db):
        repo = DbPyFocusRepository(legacy_db)
        session_id = repo.start_session(1, 25, "math")
        assert session_id > 0
        repo.end_session(session_id, 25, completed=True)


class TestFocusEvents:
    def test_orm_record_event(self, orm_session):
        repo = SqlAlchemyFocusRepository(orm_session)
        session_id = repo.start_session("u1", 25)
        orm_session.commit()
        repo.record_event(session_id, "deep", 85.0, {"duration": 20})
        orm_session.commit()
        events = repo.get_events(session_id)
        assert len(events) == 1
        assert events[0]["event_type"] == "deep"
        assert events[0]["flow_score"] == 85.0

    def test_legacy_record_event(self, legacy_db):
        repo = DbPyFocusRepository(legacy_db)
        session_id = repo.start_session(1, 25)
        repo.record_event(session_id, "deep", 80.0, {"duration": 18})
        events = repo.get_events(session_id)
        assert len(events) == 1


class TestFocusHistory:
    def test_orm_get_empty_history(self, orm_session):
        repo = SqlAlchemyFocusRepository(orm_session)
        assert repo.get_history("u1", 7) == []

    def test_legacy_get_empty_history(self, legacy_db):
        repo = DbPyFocusRepository(legacy_db)
        assert repo.get_history(1, 7) == []