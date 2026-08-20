"""Repository tests for chat (M9)."""
from __future__ import annotations

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
from app.models.chat import ChatMessage, UserMemory
from app.repositories.legacy.chat import DbPyChatRepository
from app.repositories.orm.chat import SqlAlchemyChatRepository


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


class TestChatMessages:
    def test_orm_save_message(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        msg_id = repo.save_message("u1", {
            "role": "user",
            "content": "Hello world",
            "metadata": {"source": "test"},
        })
        orm_session.commit()
        assert msg_id > 0
        history = repo.get_history("u1")
        assert len(history) == 1
        assert history[0]["content"] == "Hello world"
        assert history[0]["metadata"]["source"] == "test"

    def test_legacy_save_message(self, legacy_db):
        repo = DbPyChatRepository(legacy_db)
        msg_id = repo.save_message(1, {"role": "user", "content": "Hi"})
        # 真实 messages.id 是 TEXT PK（db.save_message 生成 uuid），不再是自增 int。
        assert isinstance(msg_id, str) and msg_id
        history = repo.get_history(1)
        assert len(history) == 1

    def test_orm_metadata_column_name(self):
        """Verify the column is msg_metadata, not metadata (reserved name)."""
        assert hasattr(ChatMessage, "msg_metadata")
        # The SQLAlchemy declarative base declares a class attribute named
        # ``metadata`` (it's the MetaData registry) — that does NOT collide
        # with our column since the column attribute is ``msg_metadata``.
        # We verify the column is named correctly in the table.
        col_names = {c.name for c in ChatMessage.__table__.columns}
        assert "msg_metadata" in col_names
        assert "metadata" not in col_names


class TestMemories:
    def test_orm_save_and_get_memory(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        mem_id = repo.save_memory("u1", {
            "memory_type": "preference",
            "content": "Likes math",
            "importance": 5,
        })
        orm_session.commit()
        memories = repo.get_memories("u1")
        assert len(memories) == 1
        assert memories[0]["content"] == "Likes math"
        assert memories[0]["importance"] == 5

    def test_legacy_save_and_get_memory(self, legacy_db):
        repo = DbPyChatRepository(legacy_db)
        repo.save_memory(1, {"memory_type": "fact", "content": "Test"})
        memories = repo.get_memories(1)
        assert len(memories) == 1

    def test_orm_update_memory(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        mem_id = repo.save_memory("u1", {"content": "Original"})
        orm_session.commit()
        repo.update_memory(mem_id, {"content": "Updated", "importance": 3})
        orm_session.commit()
        memories = repo.get_memories("u1")
        assert memories[0]["content"] == "Updated"
        assert memories[0]["importance"] == 3

    def test_orm_save_memory_returns_id(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        mem_id = repo.save_memory("u1", {"content": "x"})
        orm_session.commit()
        assert mem_id > 0


class TestProtocolCompliance:
    def test_orm_implements_protocol(self):
        """Verify SqlAlchemyChatRepository implements the Protocol methods."""
        from app.repositories.base import ChatRepository
        from app.repositories.orm.chat import SqlAlchemyChatRepository
        repo = SqlAlchemyChatRepository.__dict__
        required = {"save_message", "get_history", "save_memory", "get_memories", "update_memory"}
        for m in required:
            assert m in repo, f"missing method: {m}"

    def test_legacy_implements_protocol(self):
        from app.repositories.legacy.chat import DbPyChatRepository
        repo = DbPyChatRepository.__dict__
        required = {"save_message", "get_history", "save_memory", "get_memories", "update_memory"}
        for m in required:
            assert m in repo, f"missing method: {m}"