"""Tests for the datacenter aggregator service (Task C2).

Verifies the aggregator returns the 5-field shape consumed by
``_build_dashboard`` and pulls ``learning_record`` through the
LearningRepository Protocol (already migrated in B7).
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.services.datacenter_aggregator import build_full_user_state


class FakeLearningRepository:
    def __init__(self):
        self.calls = []
        self.learning_record = {"interaction_count": 7, "profile_json": {"x": 1}}

    def get_learning_record(self, user_id):
        self.calls.append(("get_learning_record", user_id))
        return self.learning_record


@pytest.fixture
def fake_learning(monkeypatch):
    repo = FakeLearningRepository()

    def factory(user_id: str, repository_type: str):
        return repo

    monkeypatch.setattr(
        "app.services.datacenter_aggregator.get_repository_for_user", factory
    )
    return repo


@pytest.fixture
def patched_db(monkeypatch):
    """Patch db.py helpers used by the aggregator with deterministic values."""

    def get_user_profile(uid):
        return {"user_id": uid, "profile_json": '{"learning_portrait": {}}'}

    def get_user_stats(uid):
        return {"streakDays": 3, "completedTasks": 12, "daily_minutes": {"2026-07-14": 30}}

    def get_user_focus_history(uid):
        return [{"timestamp": "2026-07-14T10:00:00", "studyMinutes": 25, "focusMinutes": 20, "pageSwitches": 1}]

    monkeypatch.setattr("db.get_user_profile", get_user_profile)
    monkeypatch.setattr("db.get_user_stats", get_user_stats)
    monkeypatch.setattr("db.get_user_focus_history", get_user_focus_history)


def test_aggregator_returns_5_field_shape(fake_learning, patched_db):
    state = build_full_user_state(7)
    assert set(state.keys()) == {"user", "stats", "focus_history", "learning_profile", "learning_record"}
    assert state["user"] is None
    assert state["stats"]["streakDays"] == 3
    assert isinstance(state["focus_history"], list) and state["focus_history"][0]["studyMinutes"] == 25
    assert state["learning_profile"]["profile_json"] == '{"learning_portrait": {}}'
    assert state["learning_record"]["interaction_count"] == 7


def test_aggregator_routes_learning_record_through_repo(fake_learning, patched_db):
    build_full_user_state("u1")
    assert ("get_learning_record", "u1") in fake_learning.calls


def test_aggregator_handles_missing_record(fake_learning, patched_db):
    fake_learning.learning_record = None
    state = build_full_user_state("u1")
    assert state["learning_record"] is None


def test_datacenter_api_uses_aggregator():
    """datacenter.py must call the aggregator instead of ``db.get_full_user_state``."""
    source = Path("app/api/datacenter.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    found_db_full_user_state = False
    found_aggregator = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "get_full_user_state":
                    found_db_full_user_state = True
            if isinstance(node.func, ast.Name) and node.func.id == "build_full_user_state":
                found_aggregator = True
            if isinstance(node.func, ast.Attribute) and node.func.attr == "build_full_user_state":
                found_aggregator = True

    assert not found_db_full_user_state, "datacenter.py still calls db.get_full_user_state"
    assert found_aggregator, "datacenter.py does not call build_full_user_state"
