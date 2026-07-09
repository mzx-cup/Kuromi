import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.repositories.legacy.preferences import DbPyPreferencesRepository
from app.repositories.orm.preferences import SqlAlchemyPreferencesRepository


@pytest.fixture
def orm_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def legacy_db(tmp_path):
    from tests.fixtures.seed_data import init_legacy_schema
    db_path = str(tmp_path / "legacy.db")
    init_legacy_schema(db_path)
    yield db_path


class TestSqlAlchemyPreferencesRepository:
    def test_set_and_get_preference(self, orm_session):
        repo = SqlAlchemyPreferencesRepository(orm_session)
        repo.set_preference("user_1", "language", {"value": "zh-CN"})
        result = repo.get_preferences("user_1")
        assert result.get("language") == {"value": "zh-CN"}

    def test_get_preferences_empty_user(self, orm_session):
        repo = SqlAlchemyPreferencesRepository(orm_session)
        assert repo.get_preferences("ghost") == {}

    def test_set_and_get_setting(self, orm_session):
        repo = SqlAlchemyPreferencesRepository(orm_session)
        repo.set_setting("user_1", "theme", "dark")
        result = repo.get_settings("user_1")
        assert result.get("theme") == "dark"

    def test_set_and_get_theme(self, orm_session):
        repo = SqlAlchemyPreferencesRepository(orm_session)
        repo.set_theme("user_1", "light", "#3b82f6")
        result = repo.get_theme("user_1")
        assert result["theme"] == "light"
        assert result["accent_color"] == "#3b82f6"

    def test_get_theme_default_when_missing(self, orm_session):
        repo = SqlAlchemyPreferencesRepository(orm_session)
        result = repo.get_theme("ghost")
        assert result["theme"] == "dark"
        assert result["accent_color"] == "#7c3aed"


class TestDbPyPreferencesRepository:
    def test_set_and_get_preference(self, legacy_db):
        repo = DbPyPreferencesRepository(legacy_db)
        repo.set_preference(1, "language", {"value": "en-US"})
        result = repo.get_preferences(1)
        assert result.get("language") == {"value": "en-US"}

    def test_set_and_get_setting(self, legacy_db):
        repo = DbPyPreferencesRepository(legacy_db)
        repo.set_setting(1, "theme", "light")
        result = repo.get_settings(1)
        assert result.get("theme") == "light"

    def test_set_and_get_theme(self, legacy_db):
        repo = DbPyPreferencesRepository(legacy_db)
        repo.set_theme(1, "ocean", "#06b6d4")
        result = repo.get_theme(1)
        assert result["theme"] == "ocean"
        assert result["accent_color"] == "#06b6d4"
