"""Unit tests for CapabilityRepository (ORM + Legacy)."""
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest
from app.repositories.base import CapabilityRepository


@pytest.fixture
def sample_user_id() -> str:
    return "test_user_capability_001"


@pytest.fixture
def legacy_db_path(tmp_path: Path) -> str:
    """真实 layer-1 schema（重放 storage/xingshi.db 的 DDL）+ 真实列 seed。

    旧版本手写"想象 schema"（learning_records 有 activity_type/minutes、
    learning_goals 有 deadline）—— 这些列在真实库中不存在，测试一直在
    验证假想世界。真实数据家：knowledge_base/focus/weakness ←
    study_sessions；code_skill/cognitive_style ← learning_records 画像表；
    learning_goals ← learning_goals(goal_type/end_date/is_active)。
    """
    from tests.fixtures.seed_data import init_legacy_schema

    db_path = str(tmp_path / "xingshi.db")
    init_legacy_schema(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Seed: knowledge base / focus / weakness (study_sessions 真实列)
    cur.executemany(
        "INSERT INTO study_sessions (user_id, subject, duration_minutes, session_date, start_time, end_time) VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("u1", "math", 120, "2026-07-01", "2026-07-01T10:00:00", "2026-07-01T12:00:00"),
            ("u1", "math", 60, "2026-07-02", "2026-07-02T10:00:00", "2026-07-02T11:00:00"),
            ("u1", "physics", 30, "2026-07-03", "2026-07-03T10:00:00", "2026-07-03T10:30:00"),
        ],
    )
    # Seed: code_skill / cognitive_style（learning_records 画像表真实列）
    cur.execute(
        "INSERT INTO learning_records (user_id, interaction_count, code_practice_time, socratic_pass_rate, difficulty_level, profile_json) VALUES (?, ?, ?, ?, ?, ?)",
        ("u1", 10, 90, 0.8, "basic", '{"modality": "visual", "depth": "deep"}'),
    )
    # Seed: learning_goals（真实列：goal_type/start_date/end_date/is_active，无 deadline）
    cur.execute(
        "INSERT INTO learning_goals (user_id, goal_type, title, target_value, current_value, unit, start_date, end_date, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)",
        ("u1", "subject", "高考数学", 100, 42, "problems", "2026-07-01", "2026-08-30"),
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
    async def test_get_code_skill_reads_profile_table(self, legacy_db_path):
        """真实 schema：learning_records 是学习画像表，只有 code_practice_time
        标量（无 per-language 数据）—— 返回 {"code": 0-1}（300 分钟封顶）。"""
        from app.repositories.legacy.capability import DbPyCapabilityRepository
        repo = DbPyCapabilityRepository(db_path=legacy_db_path)
        cs = await repo.get_code_skill("u1")
        assert cs == {"code": 0.3}

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


@pytest.fixture
def orm_db_path(tmp_path: Path) -> str:
    """Create a SQLAlchemy-style xingshi_v2.db with seed data."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.base import Base
    from app.models.learning import StudySession, LearningRecord, LearningGoal

    db_path = str(tmp_path / "xingshi_v2.db")
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        for sub, mins, dt in [("math", 120, "2026-07-01"), ("math", 60, "2026-07-02"), ("physics", 30, "2026-07-03")]:
            session.add(StudySession(
                user_id="u1", subject=sub, duration_minutes=mins,
                session_date=datetime.fromisoformat(dt).date(),
                created_at=datetime.utcnow(),
            ))
        for sub, mins in [("python", 90), ("javascript", 30)]:
            session.add(LearningRecord(
                user_id="u1", activity_type="code", subject=sub,
                minutes=mins, metadata_json={}, recorded_at=datetime.utcnow(),
            ))
        session.add(LearningGoal(
            user_id="u1", title="高考数学", target_value=100,
            current_value=42, unit="problems", deadline=datetime.fromisoformat("2026-08-30").date(),
            created_at=datetime.utcnow(),
        ))
        session.commit()
    finally:
        session.close()
    engine.dispose()
    return db_path


class TestSqlAlchemyCapabilityRepository:
    @pytest.mark.asyncio
    async def test_get_knowledge_base_aggregates_by_subject(self, orm_db_path):
        from app.repositories.orm.capability import SqlAlchemyCapabilityRepository
        repo = SqlAlchemyCapabilityRepository(db_path=orm_db_path)
        kb = await repo.get_knowledge_base("u1")
        assert "math" in kb
        assert kb["math"] > kb["physics"]

    @pytest.mark.asyncio
    async def test_get_code_skill_aggregates_by_language(self, orm_db_path):
        from app.repositories.orm.capability import SqlAlchemyCapabilityRepository
        repo = SqlAlchemyCapabilityRepository(db_path=orm_db_path)
        cs = await repo.get_code_skill("u1")
        assert "python" in cs

    @pytest.mark.asyncio
    async def test_aggregate_profile_returns_all_6_dims(self, orm_db_path):
        from app.repositories.orm.capability import SqlAlchemyCapabilityRepository
        repo = SqlAlchemyCapabilityRepository(db_path=orm_db_path)
        profile = await repo.aggregate_profile("u1")
        for dim in ("knowledge_base", "code_skill", "cognitive_style", "focus_level", "learning_goals", "weakness"):
            assert dim in profile, f"Missing dim: {dim}"

    @pytest.mark.asyncio
    async def test_legacy_and_orm_return_consistent_shape(self, legacy_db_path, orm_db_path):
        from app.repositories.legacy.capability import DbPyCapabilityRepository
        from app.repositories.orm.capability import SqlAlchemyCapabilityRepository
        legacy_repo = DbPyCapabilityRepository(db_path=legacy_db_path)
        orm_repo = SqlAlchemyCapabilityRepository(db_path=orm_db_path)
        lp = await legacy_repo.aggregate_profile("u1")
        op = await orm_repo.aggregate_profile("u1")
        assert set(lp.keys()) == set(op.keys())
        for key in lp:
            assert type(lp[key]) == type(op[key])
