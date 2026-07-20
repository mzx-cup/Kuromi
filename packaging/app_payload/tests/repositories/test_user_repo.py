import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.user import User
from app.repositories.legacy.user import DbPyUserRepository
from app.repositories.orm.user import SqlAlchemyUserRepository


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
def legacy_session(tmp_path):
    from tests.fixtures.seed_data import init_legacy_schema, populate_legacy
    db_path = str(tmp_path / "legacy.db")
    init_legacy_schema(db_path)
    populate_legacy(db_path)
    yield db_path


class TestSqlAlchemyUserRepository:
    def test_create_user(self, orm_session):
        repo = SqlAlchemyUserRepository(orm_session)
        user_id = repo.create_user(
            username="new_user",
            password_hash="hashed_pw",
            preferred_language="zh-CN",
        )
        assert user_id.startswith("orm-")

    def test_get_by_username(self, orm_session):
        repo = SqlAlchemyUserRepository(orm_session)
        repo.create_user(username="lookup_user", password_hash="h")
        found = repo.get_by_username("lookup_user")
        assert found is not None
        assert found.username == "lookup_user"

    def test_get_by_username_returns_none_for_missing(self, orm_session):
        repo = SqlAlchemyUserRepository(orm_session)
        assert repo.get_by_username("ghost") is None

    def test_record_login(self, orm_session):
        repo = SqlAlchemyUserRepository(orm_session)
        user_id = repo.create_user(username="login_rec", password_hash="h")
        repo.record_login(user_id=user_id, ip="127.0.0.1", user_agent="test")
        history = repo.get_login_history(user_id)
        assert len(history) == 1


class TestDbPyUserRepository:
    def test_create_and_lookup(self, legacy_session):
        repo = DbPyUserRepository(legacy_session)
        legacy_id = repo.create_user(
            username="legacy_user",
            password_hash="hashed_pw",
            preferred_language="zh-CN",
        )
        assert isinstance(legacy_id, int)

        found = repo.get_by_username("legacy_user")
        assert found is not None
        assert found["username"] == "legacy_user"
