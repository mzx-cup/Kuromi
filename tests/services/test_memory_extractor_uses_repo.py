"""Test that memory_extractor.save_extracted_memories routes the fallback
path through the ChatRepository (DbPyChatRepository), not raw db.py
functions (Task B2).

The primary ORM path is already exercised elsewhere (slice #9); this test
focuses on the db.py fallback that remains for callers without an ORM
session (unit tests).

Notable id-type change: the original fallback used ``f"mem_{uuid}"`` string
ids; routing through ChatRepository.save_memory returns the auto-increment
INTEGER primary key from the legacy ``user_memories`` table. The new
behaviour returns ``str(int_id)`` instead of a uuid string. This is
documented in the test names and is an intentional consequence of moving
onto the Repository abstraction.
"""
from __future__ import annotations

import asyncio
import sqlite3

import pytest


@pytest.fixture
def legacy_db(tmp_path, monkeypatch):
    """A legacy sqlite DB whose ``user_memories`` table mirrors the schema
    used by both DbPyChatRepository.save_memory (integer id, importance,
    source_conversation_id) and db.py save_user_memory (source, confidence).

    Pointing db.SQLITE_PATH at this file keeps db.get_db() resolvable in
    case any path under test still touches it; we monkeypatch
    ``_effective_backend`` to "sqlite" so the memoized config is overridden.
    """
    import db as dbmod

    db_path = str(tmp_path / "mem_fallback.db")
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
    monkeypatch.setattr(dbmod, "_effective_backend", "sqlite")
    yield db_path


def _force_fallback(monkeypatch):
    """Force the save_extracted_memories code to skip the ORM path and
    fall through to the legacy code path by making get_sessionmaker raise.
    """
    from app.core import database as dbmod
    monkeypatch.setattr(
        dbmod,
        "get_sessionmaker",
        lambda: (_ for _ in ()).throw(RuntimeError("no ORM session")),
    )


def _patch_legacy_repo_default(monkeypatch, db_path):
    """Make ``DbPyChatRepository()`` (no args) point at the test db.

    The fallback path instantiates ``DbPyChatRepository()`` with no
    arguments so it would otherwise default to ``xingshi.db`` in cwd.
    """
    from app.repositories.legacy import chat as legacy_chat
    original_init = legacy_chat.DbPyChatRepository.__init__

    def patched_init(self, db_path_arg=None):
        original_init(self, db_path_arg or db_path)

    monkeypatch.setattr(legacy_chat.DbPyChatRepository, "__init__", patched_init)


class TestFallbackUsesChatRepository:
    def test_fallback_saves_new_memory_via_repository(self, legacy_db, monkeypatch):
        """The fallback path must save memories through the legacy
        ``DbPyChatRepository.save_memory``, not by calling
        ``db.save_user_memory`` directly.
        """
        _force_fallback(monkeypatch)
        _patch_legacy_repo_default(monkeypatch, legacy_db)

        from app.services.memory_extractor import save_extracted_memories

        ids = asyncio.run(
            save_extracted_memories(
                user_id="1",
                memories=[
                    {"memory_type": "knowledge", "content": "Likes math", "confidence": 0.9}
                ],
                source="test",
            )
        )

        # New id is the stringified integer PK from user_memories.
        assert len(ids) == 1
        assert ids[0].isdigit(), f"Expected int PK string, got {ids[0]!r}"

        # Verify the row landed in the legacy user_memories table.
        conn = sqlite3.connect(legacy_db)
        try:
            row = conn.execute(
                "SELECT user_id, memory_type, content, importance, source_conversation_id "
                "FROM user_memories"
            ).fetchone()
        finally:
            conn.close()
        assert row is not None
        assert row[0] == "1"
        assert row[1] == "knowledge"
        assert row[2] == "Likes math"
        # importance = round(confidence * 10) = 9
        assert row[3] == 9
        # source_conversation_id comes from the source kwarg
        assert row[4] == "test"

    def test_fallback_updates_existing_memory_via_repository(
        self, legacy_db, monkeypatch
    ):
        """When ``is_update=True`` and ``_update_target_id`` is set, the
        fallback must update via ``DbPyChatRepository.update_memory``,
        not by calling ``db.update_user_memory`` directly.
        """
        _force_fallback(monkeypatch)
        _patch_legacy_repo_default(monkeypatch, legacy_db)

        from app.repositories.legacy.chat import DbPyChatRepository
        from app.services.memory_extractor import save_extracted_memories

        # Seed an existing memory via the repository to get a real int PK.
        seeded_id = DbPyChatRepository(legacy_db).save_memory(
            "1",
            {
                "memory_type": "knowledge",
                "content": "Likes algebra",
                "importance": 5,
            },
        )
        assert isinstance(seeded_id, int)

        # Call the extractor with an update intent.
        ids = asyncio.run(
            save_extracted_memories(
                user_id="1",
                memories=[
                    {
                        "memory_type": "knowledge",
                        "content": "Likes calculus",
                        "confidence": 0.8,
                        "is_update": True,
                        "_update_target_id": seeded_id,
                    }
                ],
                source="test",
            )
        )

        # Update path returns the same id that was passed in.
        assert ids == [seeded_id]

        # Row count is still 1 (no duplicate) and content is the new one.
        conn = sqlite3.connect(legacy_db)
        try:
            rows = conn.execute(
                "SELECT id, content, importance FROM user_memories ORDER BY id"
            ).fetchall()
        finally:
            conn.close()
        assert len(rows) == 1
        assert rows[0][0] == seeded_id
        assert rows[0][1] == "Likes calculus"
        # importance = round(0.8 * 10) = 8
        assert rows[0][2] == 8

    def test_fallback_does_not_call_db_module(self, legacy_db, monkeypatch):
        """Guard against regressions: the fallback must not import
        ``db.save_user_memory`` or ``db.update_user_memory``. We block
        those names on the ``db`` module and assert the call succeeds.
        """
        import db as dbmod
        from unittest.mock import MagicMock

        # Replace the two functions on db with sentinels that raise if called.
        def _explode(*args, **kwargs):
            raise AssertionError(
                "db.save_user_memory/update_user_memory must not be called "
                "in the fallback path — use ChatRepository instead"
            )

        monkeypatch.setattr(dbmod, "save_user_memory", _explode, raising=False)
        monkeypatch.setattr(dbmod, "update_user_memory", _explode, raising=False)

        _force_fallback(monkeypatch)
        _patch_legacy_repo_default(monkeypatch, legacy_db)

        from app.services.memory_extractor import save_extracted_memories

        # Should not raise — and should produce exactly one row.
        ids = asyncio.run(
            save_extracted_memories(
                user_id="1",
                memories=[
                    {"memory_type": "fact", "content": "x", "confidence": 0.5}
                ],
                source="test",
            )
        )
        assert len(ids) == 1

        conn = sqlite3.connect(legacy_db)
        try:
            count = conn.execute("SELECT COUNT(*) FROM user_memories").fetchone()[0]
        finally:
            conn.close()
        assert count == 1
