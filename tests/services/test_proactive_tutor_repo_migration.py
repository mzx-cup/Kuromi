"""Regression tests: proactive_tutor uses Repository abstraction, not db.py."""
import sqlite3
import pytest
from pathlib import Path


@pytest.fixture
def legacy_db_path(tmp_path: Path) -> str:
    db_path = str(tmp_path / "xingshi.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE learning_records (
            id INTEGER PRIMARY KEY,
            user_id TEXT,
            profile_json TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        INSERT INTO learning_records (user_id, profile_json, created_at) VALUES (?, ?, ?)
    """, ("u1", '{"topic": "algebra"}', "2026-06-01"))
    conn.commit()
    conn.close()
    return db_path


@pytest.mark.asyncio
async def test_query_stale_knowledge_uses_repository(monkeypatch, legacy_db_path):
    """proactive_tutor._query_stale_knowledge must NOT import from db.

    We patch sys.modules['db'] to raise ImportError on any access. The legacy
    implementation did `from db import get_db` inside a `try/except Exception`,
    so the exception was swallowed silently and the test would incorrectly
    pass. To detect the regression we also assert that the result came from
    the Repository path (not the fallback) — i.e. it includes the seeded
    'algebra' knowledge point rather than an empty list.
    """
    monkeypatch.setenv("READ_BACKEND_PERCENTAGE", "0")
    monkeypatch.setenv("XINGSHI_DB_PATH", legacy_db_path)
    # Patch the db.py module to make any import raise
    import sys
    original_db = sys.modules.get("db")
    class DBImportError:
        def __getattr__(self, name):
            raise ImportError("proactive_tutor must not use db.py directly")
    sys.modules["db"] = DBImportError()
    try:
        from unittest.mock import MagicMock
        from proactive_tutor import ProactiveTutor
        tutor = ProactiveTutor(manager=MagicMock())
        result = await tutor._query_stale_knowledge("u1", "course_1")
        # Must not raise (i.e. must not propagate the ImportError from db).
        assert isinstance(result, list)
        # Should have read the seeded record via the Repository (not the
        # fallback), proving that the data path went through the Repository
        # abstraction and never touched the (blocked) `db` module.
        assert any(
            r.get("knowledge_point") == "algebra" for r in result
        ), f"Repository path was not used; got {result!r}"
    finally:
        if original_db is not None:
            sys.modules["db"] = original_db
        else:
            del sys.modules["db"]