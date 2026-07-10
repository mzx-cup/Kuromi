import sqlite3
import pytest
from pathlib import Path


@pytest.fixture
def legacy_db(tmp_path):
    """Create a legacy db with user table."""
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(128) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            preferred_language VARCHAR(16) DEFAULT 'zh-CN'
        )
    """)
    conn.execute("INSERT INTO user (username, password) VALUES ('alice', 'hashed_pw_1')")
    conn.execute("INSERT INTO user (username, password) VALUES ('bob', 'hashed_pw_2')")
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def orm_db(tmp_path):
    """Create an ORM db with users table."""
    db_path = tmp_path / "orm.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE users (
            id VARCHAR(64) PRIMARY KEY,
            username VARCHAR(128) UNIQUE NOT NULL,
            password_hash VARCHAR(256) NOT NULL,
            preferred_language VARCHAR(16) DEFAULT 'zh-CN',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    return db_path


class TestMigrateUserTable:
    def test_dry_run_does_not_modify(self, legacy_db, orm_db):
        from scripts.migrate_user_table import migrate_user_table
        report = migrate_user_table(legacy_db, orm_db, dry_run=True)
        assert report["status"] == "dry_run_complete"
        assert report["users_in_legacy"] == 2
        # ORM should still be empty
        conn = sqlite3.connect(str(orm_db))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        assert cur.fetchone()[0] == 0
        conn.close()

    def test_actual_migration(self, legacy_db, orm_db):
        from scripts.migrate_user_table import migrate_user_table
        report = migrate_user_table(legacy_db, orm_db, dry_run=False)
        assert report["status"] == "complete"
        assert report["users_in_legacy"] == 2
        assert report["users_migrated"] == 2
        # Backups should be created
        assert report["backup"] is not None
        # ORM should now have 2 users
        conn = sqlite3.connect(str(orm_db))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        assert cur.fetchone()[0] == 2
        # UUIDs should be deterministic
        cur.execute("SELECT id, username FROM users ORDER BY username")
        rows = cur.fetchall()
        assert rows[0][1] == "alice"
        assert rows[0][0] == str(__import__("uuid").uuid5(__import__("uuid").NAMESPACE_DNS, "starlearn:alice"))
        conn.close()

    def test_idempotent_on_already_migrated(self, legacy_db, orm_db):
        from scripts.migrate_user_table import migrate_user_table
        # Run twice
        migrate_user_table(legacy_db, orm_db, dry_run=False)
        report2 = migrate_user_table(legacy_db, orm_db, dry_run=False)
        assert report2["users_migrated"] == 0  # No new migrations
        assert report2["users_already_in_orm"] == 2

    def test_legacy_db_not_found(self, tmp_path, orm_db):
        from scripts.migrate_user_table import migrate_user_table
        report = migrate_user_table(tmp_path / "missing.db", orm_db, dry_run=False)
        assert report["status"] == "error"
