import sqlite3
import pytest
from pathlib import Path


@pytest.fixture
def legacy_db_with_metadata(tmp_path):
    """Create a test db with old `metadata` column."""
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY,
            user_id TEXT,
            role TEXT,
            content TEXT,
            metadata TEXT,
            created_at TEXT
        )
    """)
    # Insert sample data
    conn.execute(
        "INSERT INTO messages (id, user_id, role, content, metadata) VALUES (1, 'u1', 'user', 'Hello', '{\"key\": \"value\"}')"
    )
    conn.execute(
        "INSERT INTO messages (id, user_id, role, content, metadata) VALUES (2, 'u1', 'assistant', 'Hi there', NULL)"
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def legacy_db_already_migrated(tmp_path):
    """Create a test db already using msg_metadata."""
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY,
            user_id TEXT,
            role TEXT,
            content TEXT,
            msg_metadata TEXT,
            created_at TEXT
        )
    """)
    conn.execute(
        "INSERT INTO messages (id, user_id, role, content, msg_metadata) VALUES (1, 'u1', 'user', 'Hello', '{\"k\": 1}')"
    )
    conn.commit()
    conn.close()
    return db_path


class TestMigrateMessagesMetadata:
    def test_dry_run_does_not_modify(self, legacy_db_with_metadata):
        from scripts.migrate_messages_metadata import migrate
        report = migrate(legacy_db_with_metadata, dry_run=True)
        assert report["status"] == "migrated"
        # Old column should still exist
        conn = sqlite3.connect(str(legacy_db_with_metadata))
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(messages)")
        cols = [r[1] for r in cur.fetchall()]
        assert "metadata" in cols  # dry-run didn't change anything
        conn.close()

    def test_migrate_renames_column(self, legacy_db_with_metadata):
        from scripts.migrate_messages_metadata import migrate
        report = migrate(legacy_db_with_metadata, dry_run=False)
        assert report["status"] == "migrated"
        assert report["renamed"] is True
        # New column should exist, old should not
        conn = sqlite3.connect(str(legacy_db_with_metadata))
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(messages)")
        cols = [r[1] for r in cur.fetchall()]
        assert "msg_metadata" in cols
        assert "metadata" not in cols
        # Data should be preserved
        cur.execute("SELECT msg_metadata FROM messages WHERE id = 1")
        val = cur.fetchone()[0]
        import json
        assert json.loads(val) == {"key": "value"}
        conn.close()

    def test_idempotent_on_already_migrated(self, legacy_db_already_migrated):
        from scripts.migrate_messages_metadata import migrate
        report = migrate(legacy_db_already_migrated, dry_run=False)
        assert report["status"] == "already_migrated"

    def test_handles_null_metadata(self, legacy_db_with_metadata):
        from scripts.migrate_messages_metadata import migrate
        migrate(legacy_db_with_metadata, dry_run=False)
        conn = sqlite3.connect(str(legacy_db_with_metadata))
        cur = conn.cursor()
        cur.execute("SELECT msg_metadata FROM messages WHERE id = 2")
        val = cur.fetchone()[0]
        # NULL should map to empty JSON object
        import json
        assert json.loads(val) == {}
        conn.close()