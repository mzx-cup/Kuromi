import sqlite3
import uuid
import pytest
from pathlib import Path


@pytest.fixture
def legacy_db(tmp_path):
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(128) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            preferred_language VARCHAR(16)
        )
    """)
    conn.execute("INSERT INTO user (username, password) VALUES ('alice', 'pw1')")
    conn.execute("INSERT INTO user (username, password) VALUES ('bob', 'pw2')")
    conn.commit()
    conn.close()
    return str(db_path)


@pytest.fixture
def orm_db(tmp_path):
    db_path = tmp_path / "orm.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE users (
            id VARCHAR(64) PRIMARY KEY,
            username VARCHAR(128) UNIQUE NOT NULL,
            password_hash VARCHAR(256) NOT NULL,
            preferred_language VARCHAR(16)
        )
    """)
    conn.commit()
    conn.close()
    return str(db_path)


class TestDeterministicUuid:
    def test_same_username_same_uuid(self):
        from app.services.user_migration import deterministic_uuid
        u1 = deterministic_uuid("alice")
        u2 = deterministic_uuid("alice")
        assert u1 == u2

    def test_different_username_different_uuid(self):
        from app.services.user_migration import deterministic_uuid
        u1 = deterministic_uuid("alice")
        u2 = deterministic_uuid("bob")
        assert u1 != u2


class TestCountFunctions:
    def test_count_legacy_users(self, legacy_db):
        from app.services.user_migration import count_legacy_users
        assert count_legacy_users(legacy_db) == 2

    def test_count_orm_users(self, orm_db):
        from app.services.user_migration import count_orm_users
        assert count_orm_users(orm_db) == 0


class TestValidateMigrationComplete:
    def test_incomplete_migration(self, legacy_db, orm_db):
        from app.services.user_migration import validate_migration_complete
        result = validate_migration_complete(legacy_db, orm_db)
        assert result["complete"] is False
        assert result["legacy_count"] == 2
        assert result["orm_count"] == 0
        assert "alice" in result["unmigrated_usernames"]

    def test_complete_migration(self, legacy_db, orm_db):
        # Add alice and bob to ORM
        conn = sqlite3.connect(orm_db)
        conn.execute("INSERT INTO users VALUES ('uuid1', 'alice', 'pw1', 'zh-CN')")
        conn.execute("INSERT INTO users VALUES ('uuid2', 'bob', 'pw2', 'zh-CN')")
        conn.commit()
        conn.close()

        from app.services.user_migration import validate_migration_complete
        result = validate_migration_complete(legacy_db, orm_db)
        assert result["complete"] is True
        assert result["unmigrated_usernames"] == []
