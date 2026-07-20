import sqlite3
import pytest
from pathlib import Path


@pytest.fixture
def primary_db(tmp_path):
    db_path = tmp_path / "primary.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE items (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value INTEGER
        )
    """)
    conn.execute("INSERT INTO items VALUES (1, 'alpha', 100)")
    conn.execute("INSERT INTO items VALUES (2, 'beta', 200)")
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def shadow_db_consistent(tmp_path):
    db_path = tmp_path / "shadow.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE items (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value INTEGER
        )
    """)
    conn.execute("INSERT INTO items VALUES (1, 'alpha', 100)")
    conn.execute("INSERT INTO items VALUES (2, 'beta', 200)")
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def shadow_db_missing(tmp_path):
    db_path = tmp_path / "shadow.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE items (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value INTEGER
        )
    """)
    conn.execute("INSERT INTO items VALUES (1, 'alpha', 100)")
    # Item 2 missing
    conn.commit()
    conn.close()
    return db_path


class TestReconcileDatabases:
    def test_consistent(self, primary_db, shadow_db_consistent):
        from scripts.reconcile_databases import reconcile_table
        result = reconcile_table("items", primary_db, shadow_db_consistent)
        assert result["consistent"] is True
        assert result["primary_count"] == 2
        assert result["shadow_count"] == 2

    def test_missing_in_shadow(self, primary_db, shadow_db_missing):
        from scripts.reconcile_databases import reconcile_table
        result = reconcile_table("items", primary_db, shadow_db_missing)
        assert result["consistent"] is False
        assert "2" in result["missing_in_shadow"]

    def test_divergent(self, primary_db, shadow_db_consistent):
        # Modify shadow value
        conn = sqlite3.connect(str(shadow_db_consistent))
        conn.execute("UPDATE items SET value = 999 WHERE id = 1")
        conn.commit()
        conn.close()

        from scripts.reconcile_databases import reconcile_table
        result = reconcile_table("items", primary_db, shadow_db_consistent)
        assert result["consistent"] is False
        assert len(result["divergent"]) == 1

    def test_normalize_strips_noise(self, primary_db, shadow_db_consistent):
        # Add noise fields that should be ignored
        for db in (primary_db, shadow_db_consistent):
            conn = sqlite3.connect(str(db))
            conn.execute("ALTER TABLE items ADD COLUMN updated_at TEXT")
            conn.execute("UPDATE items SET updated_at = '2026-01-01' WHERE id = 1")
            conn.commit()
            conn.close()

        from scripts.reconcile_databases import reconcile_table
        result = reconcile_table("items", primary_db, shadow_db_consistent)
        # Different updated_at values but should be normalized
        assert result["consistent"] is True