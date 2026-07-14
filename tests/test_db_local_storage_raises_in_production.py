"""Phase 2.3 — ``db.load_local_storage`` / ``db.save_local_storage`` raise in production.

Scope: when ``DUAL_WRITE_LEGACY`` is false (or unset — production cutover complete),
the JSON fallback in db.py is no longer a valid path. The functions must fail loudly
so a misconfigured deployment surfaces immediately rather than silently writing to
``local_storage.json`` and desynchronizing from the ORM-managed ``xingshi_v2.db``.

When ``DUAL_WRITE_LEGACY=true`` (dev / dual-write safety net), the original
behavior is preserved so existing tests and dev workflows keep working.

The gate is a single ``is_dual_write_enabled()`` check at the top of each
function — no migration of the call sites is required. The functions still
exist as infra-level helpers (per the standing rule that
``get_db``/``_is_sqlite``/``load_local_storage``/``save_local_storage`` stay
in db.py), they just refuse to do work in production.
"""
from __future__ import annotations

import json
import os

import pytest

import db


@pytest.fixture
def isolated_local_storage(monkeypatch, tmp_path):
    """Redirect db.LOCAL_STORAGE_PATH to a tmp file so tests don't touch the
    real local_storage.json in the project root."""
    tmp_file = tmp_path / "local_storage.json"
    monkeypatch.setattr(db, "LOCAL_STORAGE_PATH", str(tmp_file))
    return tmp_file


def test_load_local_storage_raises_when_dual_write_disabled(monkeypatch, isolated_local_storage):
    """Production cutover complete: JSON fallback must raise, not silently read."""
    monkeypatch.delenv("DUAL_WRITE_LEGACY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        db.load_local_storage()

    assert "DUAL_WRITE_LEGACY" in str(exc_info.value)
    # No file should have been read or written
    assert not isolated_local_storage.exists()


def test_save_local_storage_raises_when_dual_write_disabled(monkeypatch, isolated_local_storage):
    """Production cutover complete: writing to the JSON fallback must raise."""
    monkeypatch.delenv("DUAL_WRITE_LEGACY", raising=False)
    payload = {"users": [], "learning_records": []}

    with pytest.raises(RuntimeError) as exc_info:
        db.save_local_storage(payload)

    assert "DUAL_WRITE_LEGACY" in str(exc_info.value)
    # No file should have been written
    assert not isolated_local_storage.exists()


def test_load_local_storage_raises_when_dual_write_explicitly_false(monkeypatch, isolated_local_storage):
    """Setting DUAL_WRITE_LEGACY=false explicitly is the same as leaving it unset
    for the purpose of the gate (matches feature flag semantics)."""
    monkeypatch.setenv("DUAL_WRITE_LEGACY", "false")

    with pytest.raises(RuntimeError):
        db.load_local_storage()


def test_load_local_storage_works_when_dual_write_enabled(monkeypatch, isolated_local_storage):
    """Dev / safety-net path: original behavior preserved — reads the JSON file
    and returns the parsed dict."""
    monkeypatch.setenv("DUAL_WRITE_LEGACY", "true")
    isolated_local_storage.write_text(
        json.dumps({"users": [{"id": 1, "username": "u"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    result = db.load_local_storage()

    assert result == {"users": [{"id": 1, "username": "u"}]}


def test_save_local_storage_works_when_dual_write_enabled(monkeypatch, isolated_local_storage):
    """Dev / safety-net path: original behavior preserved — writes the JSON file."""
    monkeypatch.setenv("DUAL_WRITE_LEGACY", "true")
    payload = {"users": [{"id": 1, "username": "u"}]}

    db.save_local_storage(payload)

    assert isolated_local_storage.exists()
    assert json.loads(isolated_local_storage.read_text(encoding="utf-8")) == payload


def test_load_local_storage_returns_default_dict_when_dual_write_enabled_and_file_missing(
    monkeypatch, isolated_local_storage
):
    """Original behavior: missing file → default empty schema, not an error.
    The raise in production is a NEW behavior; the default-dict path is preserved
    for dev use."""
    monkeypatch.setenv("DUAL_WRITE_LEGACY", "true")
    # isolated_local_storage does not exist
    assert not isolated_local_storage.exists()

    result = db.load_local_storage()

    assert isinstance(result, dict)
    assert "users" in result
    assert "learning_records" in result
    assert result["users"] == []


def test_raise_message_mentions_phase_2_3(monkeypatch, isolated_local_storage):
    """Operators reading the traceback in production should be able to identify
    the gate and the migration step. Message includes the flag and the phase."""
    monkeypatch.delenv("DUAL_WRITE_LEGACY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        db.load_local_storage()

    message = str(exc_info.value)
    # The error should point the operator at the right next step
    assert "DUAL_WRITE_LEGACY" in message
    assert "Phase 2.3" in message or "local_storage.json" in message
