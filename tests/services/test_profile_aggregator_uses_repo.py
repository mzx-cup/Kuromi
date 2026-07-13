"""Test that aggregate_profile correctly consumes ChatRepository output (Task B1)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
from app.repositories.orm.chat import SqlAlchemyChatRepository
from app.services.profile_aggregator import aggregate_profile, MEMORY_TYPE_TO_CATEGORY


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


class TestAggregateProfileFromChatRepo:
    def test_returns_expected_top_level_keys(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        repo.save_memory("u1", {"memory_type": "knowledge", "content": "x"})
        orm_session.commit()
        profile = aggregate_profile(repo.get_memories("u1"))
        for key in ("last_updated", "learning_traits", "personality_traits", "goals_interests"):
            assert key in profile

    def test_knowledge_memory_maps_to_learning_traits(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        repo.save_memory("u1", {"memory_type": "knowledge", "content": "Loves algebra"})
        orm_session.commit()
        profile = aggregate_profile(repo.get_memories("u1"))
        assert len(profile["learning_traits"]) == 1
        assert profile["learning_traits"][0]["label"] == "Loves algebra"

    def test_personality_memory_maps_to_personality_traits(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        repo.save_memory("u1", {"memory_type": "personality", "content": "Curious"})
        orm_session.commit()
        profile = aggregate_profile(repo.get_memories("u1"))
        assert len(profile["personality_traits"]) == 1
        assert profile["personality_traits"][0]["label"] == "Curious"

    def test_goal_memory_maps_to_goals_interests(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        repo.save_memory("u1", {"memory_type": "goal", "content": "Become a data scientist"})
        orm_session.commit()
        profile = aggregate_profile(repo.get_memories("u1"))
        assert len(profile["goals_interests"]) == 1
        assert profile["goals_interests"][0]["label"] == "Become a data scientist"

    def test_unknown_memory_type_skipped(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        repo.save_memory("u1", {"memory_type": "garbage_unknown_type", "content": "irrelevant"})
        orm_session.commit()
        profile = aggregate_profile(repo.get_memories("u1"))
        assert profile["learning_traits"] == []
        assert profile["personality_traits"] == []
        assert profile["goals_interests"] == []

    def test_max_per_category_respected(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        for i in range(10):
            repo.save_memory("u1", {"memory_type": "knowledge", "content": f"trait-{i}"})
        orm_session.commit()
        profile = aggregate_profile(repo.get_memories("u1"), max_per_category=3)
        assert len(profile["learning_traits"]) == 3

    def test_each_trait_has_required_fields(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        repo.save_memory("u1", {
            "memory_type": "knowledge",
            "content": "test",
            "importance": 5,
        })
        orm_session.commit()
        profile = aggregate_profile(repo.get_memories("u1"))
        trait = profile["learning_traits"][0]
        for key in ("label", "score", "memory_id", "memory_type", "confidence", "access_count"):
            assert key in trait

    def test_score_uses_confidence_access_count_and_confirmed(self, orm_session):
        repo = SqlAlchemyChatRepository(orm_session)
        mem_id = repo.save_memory("u1", {"memory_type": "knowledge", "content": "x"})
        orm_session.commit()
        # Bump access and confirm
        repo.bump_memory_access(mem_id)
        repo.confirm_memory(mem_id, True)
        orm_session.commit()
        profile = aggregate_profile(repo.get_memories("u1"))
        trait = profile["learning_traits"][0]
        # access_count started at 1, bumped to 2
        assert trait["access_count"] == 2
        assert trait["score"] > 0.5  # confidence * 0.6 + access_score(0.2) + confirmed_bonus(0.1) = 0.8+