"""Repository tests for chat memory management (Task A2).

Covers the four memory-management methods added to the ChatRepository
Protocol and both implementations:

- ``get_memories(memory_type=...)`` — type-filtered read
- ``confirm_memory``
- ``delete_memory``
- ``bump_memory_access``
"""
from __future__ import annotations

import sqlite3

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
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
def legacy_db(tmp_path, monkeypatch):
    """A legacy sqlite DB whose ``user_memories`` table is a superset of the
    columns used by both ``DbPyChatRepository.save_memory`` (integer id,
    importance, source_conversation_id) and the db.py helper functions
    (source, confidence, updated_at, access_count, confirmed).

    ``db.SQLITE_PATH`` is pointed at the same file so that the confirm/delete/
    bump helpers (which route through ``db.get_db()``) and the repository's
    own ``save_memory``/``get_memories`` (which use ``self.db_path``) operate
    on one coherent database.
    """
    import db as dbmod

    db_path = str(tmp_path / "legacy_mem.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE user_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            memory_type VARCHAR(32) DEFAULT 'fact',
            content TEXT,
            importance INTEGER DEFAULT 1,
            source_conversation_id TEXT,
            source TEXT,
            confidence REAL DEFAULT 1.0,
            created_at TEXT,
            updated_at TEXT,
            last_accessed TEXT,
            access_count INTEGER DEFAULT 1,
            confirmed INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(dbmod, "SQLITE_PATH", db_path)
    # ``db.get_db()`` memoizes the resolved backend on first call; force it
    # back to "sqlite" so the delegating helpers (confirm_user_memory etc.)
    # route to our tmp file rather than a stale cached config.
    monkeypatch.setattr(dbmod, "_effective_backend", "sqlite")
    yield db_path


class TestOrmMemoryManagement:
    def test_orm_confirm_memory_sets_confirmed_to_1(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        mem_id = repo.save_memory("u1", {"content": "x"})
        orm_session.commit()
        repo.confirm_memory(mem_id, True)
        orm_session.commit()
        mems = repo.get_memories("u1")
        assert mems[0]["confirmed"] == 1

    def test_orm_confirm_memory_with_false_unsets(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        mem_id = repo.save_memory("u1", {"content": "x"})
        orm_session.commit()
        repo.confirm_memory(mem_id, True)
        orm_session.commit()
        repo.confirm_memory(mem_id, False)
        orm_session.commit()
        mems = repo.get_memories("u1")
        assert mems[0]["confirmed"] == 0

    def test_orm_delete_memory_removes_row(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        mem_id = repo.save_memory("u1", {"content": "x"})
        orm_session.commit()
        repo.delete_memory(mem_id)
        orm_session.commit()
        assert repo.get_memories("u1") == []

    def test_orm_delete_nonexistent_memory_no_error(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        repo.delete_memory(99999)  # should not raise
        orm_session.commit()

    def test_orm_bump_memory_access_increments_count(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        mem_id = repo.save_memory("u1", {"content": "x"})
        orm_session.commit()
        repo.bump_memory_access(mem_id)
        orm_session.commit()
        mems = repo.get_memories("u1")
        assert mems[0]["access_count"] == 2
        assert mems[0]["last_accessed"] is not None

    def test_orm_get_memories_filter_by_type(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        repo.save_memory("u1", {"memory_type": "fact", "content": "f"})
        repo.save_memory("u1", {"memory_type": "preference", "content": "p"})
        orm_session.commit()
        facts = repo.get_memories("u1", memory_type="fact")
        assert facts == [
            m for m in repo.get_memories("u1") if m["memory_type"] == "fact"
        ]
        assert len(facts) == 1
        assert facts[0]["content"] == "f"

    def test_orm_get_memories_no_filter_returns_all(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        repo.save_memory("u1", {"memory_type": "fact", "content": "f"})
        repo.save_memory("u1", {"memory_type": "preference", "content": "p"})
        orm_session.commit()
        assert len(repo.get_memories("u1")) == 2

    def test_orm_get_memories_returns_confirmed_field(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        repo.save_memory("u1", {"content": "x"})
        orm_session.commit()
        mems = repo.get_memories("u1")
        assert "confirmed" in mems[0]
        assert "access_count" in mems[0]


class TestLegacyMemoryManagement:
    def test_legacy_confirm_memory_via_db(self, legacy_db):
        repo = DbPyChatRepository(legacy_db)
        mem_id = repo.save_memory("1", {"memory_type": "fact", "content": "Test"})
        repo.confirm_memory(mem_id, True)
        conn = sqlite3.connect(legacy_db)
        try:
            row = conn.execute(
                "SELECT confirmed FROM user_memories WHERE id = ?", (mem_id,)
            ).fetchone()
        finally:
            conn.close()
        assert row[0] == 1

    def test_legacy_delete_memory_via_db(self, legacy_db):
        repo = DbPyChatRepository(legacy_db)
        mem_id = repo.save_memory("1", {"memory_type": "fact", "content": "Test"})
        repo.delete_memory(mem_id)
        assert repo.get_memories("1") == []

    def test_legacy_bump_memory_access_via_db(self, legacy_db):
        repo = DbPyChatRepository(legacy_db)
        mem_id = repo.save_memory("1", {"memory_type": "fact", "content": "Test"})
        repo.bump_memory_access(mem_id)
        conn = sqlite3.connect(legacy_db)
        try:
            row = conn.execute(
                "SELECT access_count FROM user_memories WHERE id = ?", (mem_id,)
            ).fetchone()
        finally:
            conn.close()
        assert row[0] == 2

    def test_legacy_get_memories_filter_by_type(self, legacy_db):
        repo = DbPyChatRepository(legacy_db)
        repo.save_memory("1", {"memory_type": "fact", "content": "f"})
        repo.save_memory("1", {"memory_type": "preference", "content": "p"})
        facts = repo.get_memories("1", memory_type="fact")
        all_mems = repo.get_memories("1")
        assert facts == [m for m in all_mems if m["memory_type"] == "fact"]
        assert len(facts) == 1
        assert facts[0]["content"] == "f"

    def test_legacy_update_content_preserves_importance(self, legacy_db):
        repo = DbPyChatRepository(legacy_db)
        mem_id = repo.save_memory(
            "1", {"memory_type": "fact", "content": "old", "importance": 5}
        )

        repo.update_memory(mem_id, {"content": "new"})

        conn = sqlite3.connect(legacy_db)
        try:
            row = conn.execute(
                "SELECT content, importance FROM user_memories WHERE id = ?",
                (mem_id,),
            ).fetchone()
        finally:
            conn.close()
        assert row == ("new", 5)


class TestProtocolCompliance:
    def test_protocol_includes_new_methods(self):
        from app.repositories.base import ChatRepository
        proto = ChatRepository.__dict__
        for m in ("confirm_memory", "delete_memory", "bump_memory_access"):
            assert m in proto, f"Protocol missing method: {m}"

    def test_get_memories_signature_has_memory_type_param(self):
        import inspect
        from app.repositories.base import ChatRepository
        sig = inspect.signature(ChatRepository.get_memories)
        assert "memory_type" in sig.parameters

    def test_orm_implements_new_methods(self):
        repo = SqlAlchemyChatRepository.__dict__
        for m in ("confirm_memory", "delete_memory", "bump_memory_access"):
            assert m in repo, f"ORM repo missing method: {m}"

    def test_legacy_implements_new_methods(self):
        repo = DbPyChatRepository.__dict__
        for m in ("confirm_memory", "delete_memory", "bump_memory_access"):
            assert m in repo, f"legacy repo missing method: {m}"
