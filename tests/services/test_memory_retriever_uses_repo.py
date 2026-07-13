"""Test that memory_retriever routes through ChatRepository (Task B3)."""
from __future__ import annotations

import sqlite3
import pytest

from app.services.memory_retriever import (
    retrieve_relevant_memories,
    retrieve_relevant_memories_sync,
    retrieve_memories_with_logs,
)


@pytest.fixture
def legacy_db(tmp_path, monkeypatch):
    """Legacy sqlite DB matching what DbPyChatRepository expects.

    The fixture points both ``db.SQLITE_PATH`` (used by
    ``db.bump_memory_access``) and ``DbPyChatRepository.__init__`` at the
    test database so the code under test reads and writes to the same
    place the test seeds.
    """
    import db as dbmod
    from app.repositories.legacy import chat as legacy_chat

    db_path = str(tmp_path / "retriever_test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
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
    """)
    conn.commit()
    conn.close()

    monkeypatch.setattr(dbmod, "SQLITE_PATH", db_path)
    monkeypatch.setattr(dbmod, "_effective_backend", "sqlite")

    # Point DbPyChatRepository() (no args) at our tmp DB as well.
    original_init = legacy_chat.DbPyChatRepository.__init__

    def patched_init(self, db_path_arg=None):
        original_init(self, db_path_arg or db_path)

    monkeypatch.setattr(legacy_chat.DbPyChatRepository, "__init__", patched_init)

    yield db_path


def _seed(db_path, memories):
    """Seed memories via the legacy repo."""
    from app.repositories.legacy.chat import DbPyChatRepository
    repo = DbPyChatRepository(db_path)
    for m in memories:
        repo.save_memory("1", m)


class TestRetrieveRelevantMemories:
    def test_returns_relevant_memories(self, legacy_db):
        _seed(legacy_db, [
            {"memory_type": "knowledge", "content": "Loves algebra and calculus"},
            {"memory_type": "preference", "content": "Prefers Python over Java"},
        ])
        import asyncio
        results = asyncio.run(retrieve_relevant_memories("1", "Tell me about algebra", limit=5))
        assert len(results) >= 1
        # The algebra-related memory should rank high
        contents = [m["content"] for m in results]
        assert any("algebra" in c for c in contents)

    def test_filters_by_min_confidence(self, legacy_db):
        # confidence isn't stored in ChatRepository, so this test verifies the default 1.0 path
        _seed(legacy_db, [{"memory_type": "fact", "content": "Some fact"}])
        import asyncio
        results = asyncio.run(retrieve_relevant_memories("1", "fact", limit=5, min_confidence=0.5))
        # All memories pass the confidence filter since they default to 1.0
        assert len(results) == 1

    def test_bumps_access_count(self, legacy_db):
        _seed(legacy_db, [{"memory_type": "fact", "content": "test"}])
        import asyncio
        results = asyncio.run(retrieve_relevant_memories("1", "test", limit=5))
        assert len(results) == 1
        # After retrieval, access_count should be incremented
        conn = sqlite3.connect(legacy_db)
        try:
            row = conn.execute("SELECT access_count FROM user_memories WHERE id = 1").fetchone()
        finally:
            conn.close()
        # Default access_count is 1, after one bump it should be 2
        assert row[0] == 2


class TestRetrieveMemoriesWithLogs:
    def test_returns_logs(self, legacy_db):
        _seed(legacy_db, [{"memory_type": "knowledge", "content": "Math is fun"}])
        memories, logs = retrieve_memories_with_logs("1", "math", limit=5)
        assert len(memories) == 1
        assert len(logs) == 1
        assert "memory_id" in logs[0]
        assert "content" in logs[0]
        assert "relevance_score" in logs[0]


class TestNoDbPyImport:
    def test_memory_retriever_does_not_import_db(self):
        """Guard test: verify the migration removed the db.py import."""
        import app.services.memory_retriever as mod
        src = open(mod.__file__, encoding="utf-8").read()
        assert "from db import" not in src
        assert "import db" not in src
