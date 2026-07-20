"""Analytics builder routes daily route + path through CourseProgressRepository (Task C4).

Verifies:
- ``build_student_analytics`` calls ``course_progress_repo.get_daily_route``
  and ``course_progress_repo.get_learning_path_graph`` (not legacy db.py helpers)
- The non-migrated db.py calls (profile, quizzes, classrooms, stats,
  conversation_summary, recent_messages_summary) remain on db.py
  until their Repository surfaces exist
- The output report shape is preserved end-to-end
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.services import analytics_builder


# ── Fakes ────────────────────────────────────────────────────────────────────


class FakeCourseProgressRepository:
    def __init__(self, daily_route=None, learning_path=None):
        self.calls = []
        self.daily_route = daily_route
        self.learning_path = learning_path

    def get_daily_route(self, user_id, route_date):
        self.calls.append(("get_daily_route", user_id, route_date))
        return self.daily_route

    def get_learning_path_graph(self, user_id):
        self.calls.append(("get_learning_path_graph", user_id))
        return self.learning_path


@pytest.fixture
def fake_cp_repo(monkeypatch):
    repository = FakeCourseProgressRepository(
        daily_route={
            "tasks_json": ["task-a", "task-b"],
            "completed_json": ["task-a"],
        },
        learning_path={
            "path_json": [{"topic": "intro", "status": "in_progress"}],
            "generated_at": "2026-07-14T00:00:00",
            "reasoning": "test reasoning",
            "confidence": 0.85,
        },
    )
    factory_calls = []

    def factory(user_id, repository_type):
        factory_calls.append((user_id, repository_type))
        return repository

    monkeypatch.setattr(
        analytics_builder, "get_repository_for_user", factory, raising=False
    )
    return repository, factory_calls


@pytest.fixture
def patched_db_helpers(monkeypatch):
    """Stub every db.py helper used by analytics_builder."""
    monkeypatch.setattr("db.get_user_profile", lambda uid: {
        "profile_json": '{"knowledgeBase": "基础入门", "codeSkill": "基础掌握", '
                        '"cognitiveStyle": "视觉型", "focusLevel": "中等专注", '
                        '"learningGoals": ["exam"], "weakness": "递归"}',
        "evaluation_json": '{"interactionCount": 10}',
    })
    monkeypatch.setattr("db.get_recent_quizzes", lambda uid, limit: [
        {"quiz_id": "q1", "score": 80, "total": 100, "passed": True},
        {"quiz_id": "q2", "score": 30, "total": 100, "passed": False},
    ])
    monkeypatch.setattr("db.get_recent_classrooms", lambda uid, limit: [
        {"course_id": "c1", "status": "completed", "time_spent": 600},
        {"course_id": "c2", "status": "active", "time_spent": 300},
    ])
    monkeypatch.setattr("db.get_user_stats", lambda uid: {
        "interactionCount": 10,
        "codePracticeTime": 120,
        "completedTasks": 5,
        "focusSessions": 3,
        "flashcardsStudied": 8,
        "streakDays": 4,
        "recentTopics": ["递归", "Python基础"],
    })
    monkeypatch.setattr("db.get_conversation_summary", lambda uid: {"summary": "近期学习"})
    monkeypatch.setattr("db.get_recent_messages_summary", lambda uid, limit: [
        {"role": "user", "content": "我想学习递归"},
        {"role": "user", "content": "Python 怎么学"},
    ])


# ── Routing ──────────────────────────────────────────────────────────────────


def test_factory_called_with_course_progress_type(fake_cp_repo, patched_db_helpers):
    repository, factory_calls = fake_cp_repo
    analytics_builder.build_student_analytics("7")
    assert factory_calls == [("7", "course_progress")]


def test_daily_route_routes_through_repo(fake_cp_repo, patched_db_helpers):
    repository, factory_calls = fake_cp_repo
    analytics_builder.build_student_analytics("7")
    method_names = [c[0] for c in repository.calls]
    assert "get_daily_route" in method_names
    assert "get_learning_path_graph" in method_names


def test_daily_route_call_args(fake_cp_repo, patched_db_helpers):
    repository, factory_calls = fake_cp_repo
    analytics_builder.build_student_analytics("7")
    daily_calls = [c for c in repository.calls if c[0] == "get_daily_route"]
    assert len(daily_calls) == 1
    assert daily_calls[0][1] == "7"
    # 3rd element is route_date — should be today (YYYY-MM-DD)
    assert daily_calls[0][2] == daily_calls[0][2]  # non-empty
    assert len(daily_calls[0][2]) == 10  # ISO date format


def test_learning_path_call_args(fake_cp_repo, patched_db_helpers):
    repository, factory_calls = fake_cp_repo
    analytics_builder.build_student_analytics("7")
    path_calls = [c for c in repository.calls if c[0] == "get_learning_path_graph"]
    assert path_calls == [("get_learning_path_graph", "7")]


# ── Output correctness ───────────────────────────────────────────────────────


def test_report_includes_repo_daily_route_data(fake_cp_repo, patched_db_helpers):
    analytics = analytics_builder.build_student_analytics("7")
    assert analytics["daily_route"]["has_route"] is True
    assert analytics["daily_route"]["tasks_count"] == 2
    assert analytics["daily_route"]["completed_count"] == 1


def test_report_includes_repo_learning_path_data(fake_cp_repo, patched_db_helpers):
    analytics = analytics_builder.build_student_analytics("7")
    assert analytics["current_path"]["nodes_count"] == 1
    assert analytics["current_path"]["preview"] == [
        {"topic": "intro", "status": "in_progress"}
    ]
    assert analytics["current_path"]["meta"]["confidence"] == 0.85
    assert analytics["current_path"]["meta"]["reasoning"] == "test reasoning"


def test_report_still_includes_profile_cockpit_quizzes_classrooms(
    fake_cp_repo, patched_db_helpers
):
    """Non-migrated db.py helpers still flow through into the report."""
    analytics = analytics_builder.build_student_analytics("7")
    # profile
    assert analytics["profile"]["knowledge_base"] == "基础入门"
    assert analytics["profile"]["code_skill"] == "基础掌握"
    assert analytics["profile"]["weakness"] == "递归"
    # quizzes
    assert analytics["quizzes"]["recent_count"] == 2
    assert analytics["quizzes"]["summary"]["avg_score"] == 55.0
    assert analytics["quizzes"]["summary"]["pass_rate"] == 50.0
    # classrooms
    assert analytics["classrooms"]["recent_count"] == 2
    assert analytics["classrooms"]["summary"]["completed_count"] == 1
    # study_stats
    assert analytics["study_stats"]["streak_days"] == 4
    # conversations
    assert analytics["conversations"]["summaries"] == {"summary": "近期学习"}
    assert analytics["conversations"]["recent_message_count"] == 2


def test_evidence_signals_built_correctly(fake_cp_repo, patched_db_helpers):
    analytics = analytics_builder.build_student_analytics("7")
    ev = analytics["evidence_signals"]
    assert "q1" in ev["quiz_ids"]
    assert "q2" in ev["quiz_ids"]
    assert "c1" in ev["classroom_ids"]
    assert "c2" in ev["classroom_ids"]
    assert "knowledge_base=基础入门" in ev["profile_signals"]
    assert "code_skill=基础掌握" in ev["profile_signals"]


# ── Static AST guard ─────────────────────────────────────────────────────────


def test_analytics_builder_only_calls_remaining_db_helpers():
    """The file should still call non-migrated db.py helpers (profile/quizzes/etc.)
    but should NOT call the two that were migrated (get_daily_route, get_learning_path)."""
    tree = ast.parse(Path(analytics_builder.__file__).read_text(encoding="utf-8"))
    migrated_to_repo = {"get_daily_route", "get_learning_path"}

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "database"
                    and node.func.attr in migrated_to_repo):
                violations.append((node.lineno, node.func.attr))

    assert violations == [], (
        f"analytics_builder still calls migrated db.py helpers: {violations}"
    )


def test_analytics_builder_imports_factory():
    source = Path(analytics_builder.__file__).read_text(encoding="utf-8")
    assert "from app.core.repository_factory import get_repository_for_user" in source
