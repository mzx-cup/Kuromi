"""Repository unit tests for knowledge graph + SM2 reviews (M6)."""
import sqlite3

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.knowledge import (
    KnowledgeNode,
    KnowledgeReview,
    KnowledgeRecord,
    KnowledgePending,
)
from app.models.user import User
from app.repositories.legacy.knowledge import DbPyKnowledgeRepository
from app.repositories.orm.knowledge import SqlAlchemyKnowledgeRepository


@pytest.fixture
def orm_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        session.add(User(id="u1", username="u1", password_hash="h"))
        session.commit()
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def legacy_db(tmp_path):
    from tests.fixtures.seed_data import init_legacy_schema, populate_legacy

    db_path = str(tmp_path / "legacy.db")
    init_legacy_schema(db_path)
    populate_legacy(
        db_path,
        [
            {"id": 1, "username": "u1", "password": "h", "preferred_language": "zh-CN"},
        ],
    )
    yield db_path


# ── KnowledgeNode ──


class TestKnowledgeNodeOrm:
    def test_add_and_get(self, orm_session):
        repo = SqlAlchemyKnowledgeRepository(orm_session)
        node_id = repo.add_node(
            "u1",
            {"name": "Pythagorean Theorem", "subject": "math", "importance": 5},
        )
        orm_session.commit()
        nodes = repo.get_nodes("u1")
        assert len(nodes) == 1
        assert nodes[0]["name"] == "Pythagorean Theorem"
        assert nodes[0]["importance"] == 5
        assert nodes[0]["id"] == node_id

    def test_get_empty(self, orm_session):
        repo = SqlAlchemyKnowledgeRepository(orm_session)
        assert repo.get_nodes("u1") == []

    def test_order_by_importance_then_mastery(self, orm_session):
        repo = SqlAlchemyKnowledgeRepository(orm_session)
        repo.add_node("u1", {"name": "low", "importance": 1, "mastery": 0})
        repo.add_node("u1", {"name": "high", "importance": 5, "mastery": 90})
        orm_session.commit()
        nodes = repo.get_nodes("u1")
        assert [n["name"] for n in nodes] == ["high", "low"]


class TestKnowledgeNodeLegacy:
    def test_add_and_get(self, legacy_db):
        repo = DbPyKnowledgeRepository(legacy_db)
        node_id = repo.add_node(1, {"name": "Linear Algebra", "subject": "math"})
        nodes = repo.get_nodes(1)
        assert len(nodes) == 1
        assert nodes[0]["name"] == "Linear Algebra"
        assert nodes[0]["id"] == node_id

    def test_get_empty(self, legacy_db):
        repo = DbPyKnowledgeRepository(legacy_db)
        assert repo.get_nodes(1) == []


# ── KnowledgePending ──


class TestKnowledgePendingOrm:
    def test_get_empty(self, orm_session):
        repo = SqlAlchemyKnowledgeRepository(orm_session)
        assert repo.get_pending("u1") == []

    def test_get_with_due_node(self, orm_session):
        repo = SqlAlchemyKnowledgeRepository(orm_session)
        node_id = repo.add_node("u1", {"name": "Due", "importance": 2})
        # Seed pending + review rows
        from datetime import date
        orm_session.add(KnowledgePending(user_id="u1", node_id=node_id,
                                          due_date=date.today(), priority=1))
        orm_session.commit()
        pending = repo.get_pending("u1")
        assert len(pending) == 1
        assert pending[0]["name"] == "Due"
        assert pending[0]["interval_days"] == 1


class TestKnowledgePendingLegacy:
    def test_get_empty(self, legacy_db):
        repo = DbPyKnowledgeRepository(legacy_db)
        assert repo.get_pending(1) == []

    def test_get_with_due_node(self, legacy_db):
        repo = DbPyKnowledgeRepository(legacy_db)
        node_id = repo.add_node(1, {"name": "Due"})
        from datetime import date
        conn = sqlite3.connect(legacy_db)
        conn.execute(
            "INSERT INTO knowledge_pending (user_id, node_id, due_date, priority) "
            "VALUES (?, ?, ?, ?)",
            (1, node_id, date.today().isoformat(), 0),
        )
        conn.commit()
        conn.close()
        pending = repo.get_pending(1)
        assert len(pending) == 1
        assert pending[0]["name"] == "Due"


# ── KnowledgeRecords + record_review ──


class TestKnowledgeRecordsOrm:
    def test_record_review(self, orm_session):
        repo = SqlAlchemyKnowledgeRepository(orm_session)
        node_id = repo.add_node("u1", {"name": "Test", "importance": 1})
        orm_session.commit()
        repo.record_review("u1", node_id, quality=4, ease_factor=2.5, interval_days=6)
        orm_session.commit()
        records = repo.get_records("u1")
        assert len(records) == 1
        assert records[0]["action"] == "review"
        assert records[0]["quality"] == 4

    def test_record_review_updates_existing(self, orm_session):
        repo = SqlAlchemyKnowledgeRepository(orm_session)
        node_id = repo.add_node("u1", {"name": "Repeat", "importance": 1})
        orm_session.commit()
        repo.record_review("u1", node_id, quality=3, ease_factor=2.5, interval_days=1)
        repo.record_review("u1", node_id, quality=4, ease_factor=2.6, interval_days=6)
        orm_session.commit()

        # 2 audit rows, plus a single KnowledgeReview with repetitions=2
        records = repo.get_records("u1")
        assert len(records) == 2

        review = (
            orm_session.query(KnowledgeReview)
            .filter_by(user_id="u1", node_id=node_id)
            .one()
        )
        assert review.repetitions == 2
        assert review.ease_factor == 2.6
        assert review.interval_days == 6


class TestKnowledgeRecordsLegacy:
    def test_record_review(self, legacy_db):
        repo = DbPyKnowledgeRepository(legacy_db)
        node_id = repo.add_node(1, {"name": "Test"})
        repo.record_review(1, node_id, quality=3, ease_factor=2.3, interval_days=4)
        records = repo.get_records(1)
        assert len(records) == 1
        assert records[0]["action"] == "review"
        assert records[0]["quality"] == 3

    def test_record_review_updates_existing(self, legacy_db):
        repo = DbPyKnowledgeRepository(legacy_db)
        node_id = repo.add_node(1, {"name": "Repeat"})
        repo.record_review(1, node_id, quality=3, ease_factor=2.5, interval_days=1)
        repo.record_review(1, node_id, quality=4, ease_factor=2.6, interval_days=6)
        records = repo.get_records(1)
        assert len(records) == 2

        conn = sqlite3.connect(legacy_db)
        row = conn.execute(
            "SELECT ease_factor, interval_days, repetitions FROM knowledge_reviews "
            "WHERE user_id = ? AND node_id = ?",
            (1, node_id),
        ).fetchone()
        conn.close()
        assert row[0] == 2.6
        assert row[1] == 6
        assert row[2] == 2


# ── Symmetry ──


class TestSymmetry:
    def test_node_shape_matches(self, orm_session, legacy_db):
        orm_repo = SqlAlchemyKnowledgeRepository(orm_session)
        legacy_repo = DbPyKnowledgeRepository(legacy_db)
        orm_id = orm_repo.add_node(
            "u1", {"name": "Symmetric", "subject": "math", "importance": 3}
        )
        orm_session.commit()
        legacy_id = legacy_repo.add_node(
            1, {"name": "Symmetric", "subject": "math", "importance": 3}
        )

        o = orm_repo.get_nodes("u1")[0]
        l = legacy_repo.get_nodes(1)[0]
        assert set(o.keys()) == set(l.keys())
        assert o["name"] == l["name"]
        assert o["subject"] == l["subject"]
        assert o["importance"] == l["importance"]
        assert isinstance(o["id"], int)
        assert isinstance(l["id"], int)
        assert orm_id > 0 and legacy_id > 0