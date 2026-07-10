import sqlite3
import pytest
from pathlib import Path


@pytest.fixture
def legacy_db(tmp_path):
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE user (id INTEGER PRIMARY KEY)")
    conn.execute("CREATE TABLE user_preferences (user_id INTEGER, key TEXT)")
    conn.execute("INSERT INTO user_preferences VALUES (1, 'lang')")
    conn.execute("INSERT INTO user_preferences VALUES (2, 'theme')")
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def orm_db(tmp_path):
    db_path = tmp_path / "orm.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE users (id VARCHAR(64) PRIMARY KEY)")
    conn.execute("CREATE TABLE user_preferences_orm (user_id VARCHAR(64), key TEXT)")
    conn.execute("INSERT INTO user_preferences_orm VALUES ('uuid1', 'lang')")
    conn.execute("INSERT INTO user_preferences_orm VALUES ('uuid2', 'theme')")
    conn.commit()
    conn.close()
    return db_path


class TestAuditForeignKeys:
    def test_matching_counts(self, legacy_db, orm_db):
        from scripts.audit_foreign_keys import audit
        report = audit(legacy_db, orm_db)
        assert report["match"] is True
        assert report["legacy_references"]["total"] == 2
        assert report["orm_references"]["total"] == 2

    def test_mismatched_counts(self, legacy_db, orm_db):
        # Add a row to legacy only
        conn = sqlite3.connect(str(legacy_db))
        conn.execute("INSERT INTO user_preferences VALUES (3, 'extra')")
        conn.commit()
        conn.close()

        from scripts.audit_foreign_keys import audit
        report = audit(legacy_db, orm_db)
        assert report["match"] is False
        assert report["legacy_references"]["total"] == 3
        assert report["orm_references"]["total"] == 2
