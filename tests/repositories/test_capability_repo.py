"""Unit tests for CapabilityRepository (ORM + Legacy)."""
import sqlite3
from pathlib import Path

import pytest
from app.repositories.base import CapabilityRepository


@pytest.fixture
def sample_user_id() -> str:
    return "test_user_capability_001"


@pytest.fixture
def legacy_db_path(tmp_path: Path) -> str:
    """Create a db.py-style xingshi.db with seed data."""
    db_path = str(tmp_path / "xingshi.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE study_sessions (
            id INTEGER PRIMARY KEY,
            user_id TEXT,
            subject TEXT,
            duration_minutes INTEGER,
            session_date TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE learning_records (
            id INTEGER PRIMARY KEY,
            user_id TEXT,
            activity_type TEXT,
            subject TEXT,
            minutes INTEGER,
            metadata TEXT,
            recorded_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE learning_goals (
            id INTEGER PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            target_value REAL,
            current_value REAL,
            unit TEXT,
            deadline TEXT,
            created_at TEXT
        )
    """)
    # Seed: knowledge base (study_sessions with subject)
    cur.executemany(
        "INSERT INTO study_sessions (user_id, subject, duration_minutes, session_date, created_at) VALUES (?, ?, ?, ?, ?)",
        [
            ("u1", "math", 120, "2026-07-01", "2026-07-01T10:00:00"),
            ("u1", "math", 60, "2026-07-02", "2026-07-02T10:00:00"),
            ("u1", "physics", 30, "2026-07-03", "2026-07-03T10:00:00"),
        ],
    )
    # Seed: code_skill (learning_records with activity_type='code')
    cur.executemany(
        "INSERT INTO learning_records (user_id, activity_type, subject, minutes, metadata, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("u1", "code", "python", 90, "{}", "2026-07-01T10:00:00"),
            ("u1", "code", "javascript", 30, "{}", "2026-07-02T10:00:00"),
        ],
    )
    # Seed: learning_goals
    cur.execute(
        "INSERT INTO learning_goals (user_id, title, target_value, current_value, unit, deadline, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("u1", "高考数学", 100, 42, "problems", "2026-08-30", "2026-07-01T00:00:00"),
    )
    conn.commit()
    conn.close()
    return db_path


class TestCapabilityRepositoryProtocol:
    def test_protocol_lists_required_methods(self):
        """The CapabilityRepository Protocol must define all 6 dimensions + util methods."""
        from app.repositories.base import CapabilityRepository
        assert hasattr(CapabilityRepository, "__call__")  # Protocol is callable
        from app.repositories.legacy.capability import DbPyCapabilityRepository
        from app.repositories.orm.capability import SqlAlchemyCapabilityRepository
        repo_orm = SqlAlchemyCapabilityRepository(db_path="xingshi_v2.db")
        repo_legacy = DbPyCapabilityRepository(db_path="xingshi.db")
        assert isinstance(repo_orm, CapabilityRepository)
        assert isinstance(repo_legacy, CapabilityRepository)


class TestDbPyCapabilityRepository:
    @pytest.mark.asyncio
    async def test_get_knowledge_base_aggregates_by_subject(self, legacy_db_path):
        from app.repositories.legacy.capability import DbPyCapabilityRepository
        repo = DbPyCapabilityRepository(db_path=legacy_db_path)
        kb = await repo.get_knowledge_base("u1")
        # math: 180 min, physics: 30 min — scaled to mastery
        assert "math" in kb
        assert kb["math"] > kb["physics"]

    @pytest.mark.asyncio
    async def test_get_code_skill_aggregates_by_language(self, legacy_db_path):
        from app.repositories.legacy.capability import DbPyCapabilityRepository
        repo = DbPyCapabilityRepository(db_path=legacy_db_path)
        cs = await repo.get_code_skill("u1")
        assert "python" in cs
        assert cs["python"] > cs["javascript"]

    @pytest.mark.asyncio
    async def test_get_learning_goals_returns_list(self, legacy_db_path):
        from app.repositories.legacy.capability import DbPyCapabilityRepository
        repo = DbPyCapabilityRepository(db_path=legacy_db_path)
        goals = await repo.get_learning_goals("u1")
        assert len(goals) == 1
        assert goals[0]["title"] == "高考数学"
        assert goals[0]["progress"] == pytest.approx(0.42, rel=0.01)

    @pytest.mark.asyncio
    async def test_aggregate_profile_returns_all_6_dims(self, legacy_db_path):
        from app.repositories.legacy.capability import DbPyCapabilityRepository
        repo = DbPyCapabilityRepository(db_path=legacy_db_path)
        profile = await repo.aggregate_profile("u1")
        for dim in ("knowledge_base", "code_skill", "cognitive_style", "focus_level", "learning_goals", "weakness"):
            assert dim in profile, f"Missing dim: {dim}"

    @pytest.mark.asyncio
    async def test_empty_user_returns_empty_dicts(self, legacy_db_path):
        from app.repositories.legacy.capability import DbPyCapabilityRepository
        repo = DbPyCapabilityRepository(db_path=legacy_db_path)
        profile = await repo.aggregate_profile("ghost_user")
        assert profile["knowledge_base"] == {}
        assert profile["learning_goals"] == []
