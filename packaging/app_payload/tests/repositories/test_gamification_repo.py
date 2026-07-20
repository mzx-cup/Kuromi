"""Repository tests for gamification (M8)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
from app.repositories.legacy.gamification import DbPyGamificationRepository
from app.repositories.orm.gamification import SqlAlchemyGamificationRepository


@pytest.fixture
def orm_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
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


class TestGarden:
    def test_orm_get_default(self, orm_session):
        repo = SqlAlchemyGamificationRepository(orm_session)
        result = repo.get_garden("u1")
        assert result["plants"] == {}
        assert result["growth_points"] == 0
        assert result["last_watered"] is None

    def test_legacy_get_default(self, legacy_db):
        repo = DbPyGamificationRepository(legacy_db)
        result = repo.get_garden(1)
        assert result["plants"] == {}
        assert result["growth_points"] == 0

    def test_orm_save_and_get(self, orm_session):
        repo = SqlAlchemyGamificationRepository(orm_session)
        repo.save_garden("u1", {"plants": {"rose": 3}, "growth_points": 10})
        orm_session.commit()
        result = repo.get_garden("u1")
        assert result["plants"]["rose"] == 3
        assert result["growth_points"] == 10

    def test_legacy_save_and_get(self, legacy_db):
        repo = DbPyGamificationRepository(legacy_db)
        repo.save_garden(1, {"plants": {"rose": 3}, "growth_points": 10})
        result = repo.get_garden(1)
        assert result["plants"]["rose"] == 3
        assert result["growth_points"] == 10

    def test_orm_save_updates_existing(self, orm_session):
        repo = SqlAlchemyGamificationRepository(orm_session)
        repo.save_garden("u1", {"plants": {"rose": 3}, "growth_points": 10})
        orm_session.commit()
        repo.save_garden("u1", {"plants": {"rose": 5}, "growth_points": 20})
        orm_session.commit()
        result = repo.get_garden("u1")
        assert result["plants"]["rose"] == 5
        assert result["growth_points"] == 20


class TestPet:
    def test_orm_get_default(self, orm_session):
        repo = SqlAlchemyGamificationRepository(orm_session)
        result = repo.get_pet("u1")
        assert result["name"] == "Pixel"
        assert result["level"] == 1
        assert result["happiness"] == 50.0

    def test_legacy_get_default(self, legacy_db):
        repo = DbPyGamificationRepository(legacy_db)
        result = repo.get_pet(1)
        assert result["name"] == "Pixel"
        assert result["level"] == 1

    def test_orm_save_and_get(self, orm_session):
        repo = SqlAlchemyGamificationRepository(orm_session)
        repo.save_pet("u1", {"name": "Buddy", "level": 5, "happiness": 80.0})
        orm_session.commit()
        result = repo.get_pet("u1")
        assert result["name"] == "Buddy"
        assert result["level"] == 5
        assert result["happiness"] == 80.0

    def test_legacy_save_and_get(self, legacy_db):
        repo = DbPyGamificationRepository(legacy_db)
        repo.save_pet(1, {"name": "Buddy", "level": 5, "happiness": 80.0})
        result = repo.get_pet(1)
        assert result["name"] == "Buddy"
        assert result["level"] == 5


class TestAchievements:
    def test_orm_get_default(self, orm_session):
        repo = SqlAlchemyGamificationRepository(orm_session)
        assert repo.get_achievements("u1") == []

    def test_legacy_get_default(self, legacy_db):
        repo = DbPyGamificationRepository(legacy_db)
        assert repo.get_achievements(1) == []

    def test_orm_save_and_list(self, orm_session):
        repo = SqlAlchemyGamificationRepository(orm_session)
        repo.save_achievement("u1", {"achievement_id": "first_login", "title": "Welcome!"})
        orm_session.commit()
        result = repo.get_achievements("u1")
        assert len(result) == 1
        assert result[0]["achievement_id"] == "first_login"
        assert result[0]["title"] == "Welcome!"

    def test_legacy_save_and_list(self, legacy_db):
        repo = DbPyGamificationRepository(legacy_db)
        aid = repo.save_achievement(1, {"achievement_id": "first_login", "title": "Welcome!"})
        assert aid > 0
        result = repo.get_achievements(1)
        assert len(result) == 1
        assert result[0]["achievement_id"] == "first_login"

    def test_orm_save_returns_id(self, orm_session):
        repo = SqlAlchemyGamificationRepository(orm_session)
        aid = repo.save_achievement("u1", {"achievement_id": "first_login"})
        orm_session.commit()
        assert aid > 0


class TestEco:
    def test_orm_get_default(self, orm_session):
        repo = SqlAlchemyGamificationRepository(orm_session)
        result = repo.get_eco("u1")
        assert result["eco_points"] == 0
        assert result["co2_saved_kg"] == 0.0
        assert result["level"] == "Seedling"

    def test_legacy_get_default(self, legacy_db):
        repo = DbPyGamificationRepository(legacy_db)
        result = repo.get_eco(1)
        assert result["eco_points"] == 0
        assert result["level"] == "Seedling"

    def test_orm_save_and_get(self, orm_session):
        repo = SqlAlchemyGamificationRepository(orm_session)
        repo.save_eco("u1", {"eco_points": 100, "level": "Sprout"})
        orm_session.commit()
        result = repo.get_eco("u1")
        assert result["eco_points"] == 100
        assert result["level"] == "Sprout"

    def test_legacy_save_and_get(self, legacy_db):
        repo = DbPyGamificationRepository(legacy_db)
        repo.save_eco(1, {"eco_points": 100, "level": "Sprout"})
        result = repo.get_eco(1)
        assert result["eco_points"] == 100
        assert result["level"] == "Sprout"