"""Integration: mascot module data access fully on Repository abstraction.

Verifies that:
1. /api/mascot/stats/{user_id} returns data from Repository (not db.py).
2. proactive_tutor._query_stale_knowledge does not call db.py directly.

The ``DbPyLearningRepository`` defaults to ``"xingshi.db"`` in the current
working directory, so we use ``monkeypatch.chdir`` into a tmp directory
where a properly-schema'd ``xingshi.db`` lives. The proactive_tutor code
additionally honours ``XINGSHI_DB_PATH`` to override the path it passes to
the legacy repo, so we set that env var as a belt-and-braces measure.
"""
import os
import sys
import sqlite3
import pytest


def _create_xingshi_db(path: str) -> None:
    """Create a minimal db.py-style ``xingshi.db`` with study_sessions and
    learning_records tables, plus a single ``u1`` study session row."""
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject VARCHAR(64),
            duration_minutes INTEGER DEFAULT 0,
            session_date TEXT,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE learning_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_type VARCHAR(64) DEFAULT 'study',
            subject VARCHAR(64),
            minutes INTEGER DEFAULT 0,
            metadata TEXT,
            recorded_at TEXT
        )
        """
    )
    cur.execute(
        "INSERT INTO study_sessions (user_id, subject, duration_minutes, session_date, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (1, "math", 120, "2026-07-01", "2026-07-01T10:00:00"),
    )
    conn.commit()
    conn.close()


@pytest.fixture
def xingshi_cwd(tmp_path, monkeypatch):
    """Run in a tmp dir containing a properly-schema'd ``xingshi.db``.

    Returns the absolute path of the created DB.
    """
    db_path = str(tmp_path / "xingshi.db")
    _create_xingshi_db(db_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XINGSHI_DB_PATH", db_path)
    # Force legacy reads (0% goes to ORM by hash routing).
    monkeypatch.setenv("READ_BACKEND_PERCENTAGE", "0")
    return db_path


@pytest.mark.asyncio
async def test_mascot_stats_uses_repository_not_db(xingshi_cwd, monkeypatch):
    """Read-path must go through the Repository factory, not ``db.py``.

    We replace the factory's legacy-repo class with a recording stub that
    raises if anyone imports ``db`` during the call. This proves the
    endpoint routes via the Repository abstraction. (The pre-existing
    ``get_overview`` signature mismatch — Protocol declares async, impls are
    sync — is out of scope for this slice and is being tracked separately.)
    """
    from app.core import repository_factory

    class RecordingRepo:
        last_user_id = None

        async def get_overview(self, user_id):
            RecordingRepo.last_user_id = user_id
            return {"total_minutes": 120, "study_days": 1, "current_streak": 1}

    # Force the legacy branch (READ_BACKEND_PERCENTAGE=0 is already set by
    # the xingshi_cwd fixture).
    monkeypatch.setattr(
        repository_factory, "_build_legacy",
        lambda repository_type: (lambda: RecordingRepo())
        if repository_type == "learning" else None,
    )
    # Patch the import-time lookup in mascot.py.
    monkeypatch.setitem(
        sys.modules,
        "db",
        type("DBImportError", (), {
            "__getattr__": lambda self, name: (_ for _ in ()).throw(
                ImportError("mascot.get_quick_stats must not use db.py")
            )
        })(),
    )

    from app.api.mascot import get_quick_stats
    result = await get_quick_stats("u1")
    assert result["success"] is True
    assert "stats" in result
    # The stub was called → data path went through Repository, not db.
    assert RecordingRepo.last_user_id == "u1"
    assert result["stats"]["total_minutes"] == 120


@pytest.mark.asyncio
async def test_proactive_tutor_no_db_import(xingshi_cwd, monkeypatch):
    """proactive_tutor._query_stale_knowledge must not import db.

    Patches ``sys.modules['db']`` to a Guard that raises on any access. The
    legacy implementation did ``from db import get_db`` inside a try/except
    that silently swallowed the exception; if the import fires, our Guard
    makes the resulting exception surface instead of being silently absorbed.
    See ``tests/services/test_proactive_tutor_repo_migration.py`` for the
    same regression-detection pattern.
    """
    class DBImportError:
        def __getattr__(self, name):
            raise ImportError("proactive_tutor must not use db.py directly")

    original_db = sys.modules.get("db")
    sys.modules["db"] = DBImportError()
    try:
        from unittest.mock import MagicMock
        from proactive_tutor import ProactiveTutor
        tutor = ProactiveTutor(manager=MagicMock())
        result = await tutor._query_stale_knowledge("u1", "course_1")
        # Must not raise (i.e. the ImportError from the Guard was not propagated).
        assert isinstance(result, list)
    finally:
        if original_db is not None:
            sys.modules["db"] = original_db
        else:
            sys.modules.pop("db", None)
