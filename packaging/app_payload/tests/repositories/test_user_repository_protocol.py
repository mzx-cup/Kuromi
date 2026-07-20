"""Protocol + factory wiring tests for UserRepository (Task A1)."""
from __future__ import annotations

import pytest
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.repositories.base import UserRepository
from app.repositories.legacy.user import DbPyUserRepository
from app.repositories.orm.user import SqlAlchemyUserRepository
from app.core.repository_factory import get_repository_for_user


@pytest.fixture
def orm_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


class TestUserRepositoryProtocol:
    def test_legacy_user_repo_satisfies_protocol(self, tmp_path):
        """DbPyUserRepository should satisfy UserRepository protocol."""
        # Use tmp_path for an empty SQLite that has the legacy 'user' table
        db = tmp_path / "legacy.db"
        conn = sqlite3.connect(str(db))
        conn.execute("""
            CREATE TABLE user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(128) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                preferred_language VARCHAR(16) DEFAULT 'zh-CN'
            )
        """)
        conn.execute("INSERT INTO user (username, password) VALUES ('alice', 'h')")
        conn.commit()
        conn.close()
        repo = DbPyUserRepository(str(db))
        assert isinstance(repo, UserRepository)

    def test_orm_user_repo_satisfies_protocol(self, orm_session):
        """SqlAlchemyUserRepository should satisfy UserRepository protocol."""
        repo = SqlAlchemyUserRepository(orm_session)
        assert isinstance(repo, UserRepository)


class TestFactoryUserRouting:
    def test_zero_percentage_returns_legacy_user_repo(self, monkeypatch, tmp_path):
        monkeypatch.setenv("READ_BACKEND_PERCENTAGE", "0")
        # Constructor touches db_path but the factory only calls .instantiate(),
        # so a tmp_path is fine even without a real schema.
        db = tmp_path / "legacy.db"
        monkeypatch.setattr(
            "app.repositories.legacy.user.DbPyUserRepository.__init__",
            lambda self, db_path=None: setattr(self, "db_path", str(db)),
        )
        repo = get_repository_for_user("any_user", repository_type="user")
        assert isinstance(repo, DbPyUserRepository)

    def test_hundred_percentage_returns_orm_user_repo(self, monkeypatch):
        monkeypatch.setenv("READ_BACKEND_PERCENTAGE", "100")
        repo = get_repository_for_user("any_user", repository_type="user")
        assert isinstance(repo, SqlAlchemyUserRepository)

    def test_unknown_user_repository_type_raises(self):
        """Sanity: the factory still rejects truly unknown types."""
        with pytest.raises(ValueError, match="Unknown repository_type"):
            get_repository_for_user("u1", repository_type="nonexistent_type")
