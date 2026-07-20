"""llm_analyzer and rule_engine route node ops through CourseProgressRepository (Task C5).

Verifies:
- Static AST guard: ``database.get_learning_path_node``,
  ``database.save_learning_path_node``, and ``database.get_learning_path_nodes``
  are absent from llm_analyzer.py and rule_engine.py
- The non-migrated db.py helpers (``get_recent_messages_summary``,
  ``get_recent_quizzes``, ``get_user_stats``, ``get_recent_classrooms``)
  remain on db.py until their Repository surfaces exist
- Runtime: ``apply_llm_analysis`` and ``_apply_result`` route through the repo
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.services.learning_path import llm_analyzer, rule_engine


# ── Fake repository ──────────────────────────────────────────────────────────


class FakeCourseProgressRepository:
    def __init__(self):
        self.calls = []
        self.nodes = {}
        self.daily_routes = {}

    def get_learning_path_graph(self, user_id):
        self.calls.append(("get_learning_path_graph", user_id))
        return None

    def save_learning_path_graph(self, user_id, path_json, reasoning=None,
                                 data_sources=None, confidence=0.0):
        self.calls.append(("save_learning_path_graph", user_id))
        return None

    def get_learning_path_nodes(self, user_id):
        self.calls.append(("get_learning_path_nodes", user_id))
        return self.nodes.get(user_id, [])

    def get_learning_path_node(self, user_id, node_id):
        self.calls.append(("get_learning_path_node", user_id, node_id))
        for n in self.nodes.get(user_id, []):
            if n.get("node_id") == node_id:
                return n
        return None

    def save_learning_path_node(self, user_id, node_data):
        self.calls.append(("save_learning_path_node", user_id, node_data))
        bucket = self.nodes.setdefault(user_id, [])
        nid = node_data.get("node_id")
        for i, existing in enumerate(bucket):
            if existing.get("node_id") == nid:
                bucket[i].update({k: v for k, v in node_data.items() if v is not None})
                return True
        bucket.append(dict(node_data))
        return True

    def sync_path_to_nodes(self, user_id, path_json):
        self.calls.append(("sync_path_to_nodes", user_id, path_json))
        return 0

    def get_daily_route(self, user_id, route_date):
        self.calls.append(("get_daily_route", user_id, route_date))
        return self.daily_routes.get((user_id, route_date))

    def save_daily_route(self, user_id, route_date, tasks, completed=None):
        self.calls.append(("save_daily_route", user_id, route_date))
        return None


@pytest.fixture
def fake_cp_repo(monkeypatch):
    """Patch both llm_analyzer and rule_engine to use the same fake repo."""
    repository = FakeCourseProgressRepository()
    factory_calls = []

    def factory(user_id, repository_type):
        factory_calls.append((user_id, repository_type))
        return repository

    monkeypatch.setattr(llm_analyzer, "get_repository_for_user", factory, raising=False)
    monkeypatch.setattr(rule_engine, "get_repository_for_user", factory, raising=False)
    return repository, factory_calls


# ── Static AST guard ─────────────────────────────────────────────────────────


def _collect_db_method_calls(tree):
    """Return all ``database.<method>(...)`` invocations in the AST."""
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "database":
                calls.append((node.lineno, node.func.attr))
    return calls


MIGRATED_TO_REPO = {
    "get_learning_path", "get_learning_path_nodes", "get_learning_path_node",
    "save_learning_path", "save_learning_path_node", "sync_path_to_nodes",
}


def test_llm_analyzer_no_longer_calls_migrated_db_helpers():
    tree = ast.parse(Path(llm_analyzer.__file__).read_text(encoding="utf-8"))
    violations = [
        (ln, m) for ln, m in _collect_db_method_calls(tree) if m in MIGRATED_TO_REPO
    ]
    assert violations == [], f"llm_analyzer still calls migrated db helpers: {violations}"


def test_llm_analyzer_only_calls_unmigrated_db_helpers():
    """``get_recent_messages_summary`` stays on db.py (no Repository surface)."""
    tree = ast.parse(Path(llm_analyzer.__file__).read_text(encoding="utf-8"))
    calls = _collect_db_method_calls(tree)
    assert all(m == "get_recent_messages_summary" for _, m in calls), calls
    assert len(calls) >= 1


def test_rule_engine_no_longer_calls_migrated_db_helpers():
    tree = ast.parse(Path(rule_engine.__file__).read_text(encoding="utf-8"))
    violations = [
        (ln, m) for ln, m in _collect_db_method_calls(tree) if m in MIGRATED_TO_REPO
    ]
    assert violations == [], f"rule_engine still calls migrated db helpers: {violations}"


def test_rule_engine_only_calls_unmigrated_db_helpers():
    """``get_recent_quizzes``, ``get_user_stats``, ``get_recent_classrooms`` stay."""
    tree = ast.parse(Path(rule_engine.__file__).read_text(encoding="utf-8"))
    calls = _collect_db_method_calls(tree)
    allowed = {"get_recent_quizzes", "get_user_stats", "get_recent_classrooms"}
    assert all(m in allowed for _, m in calls), calls
    assert len(calls) >= 1


def test_both_modules_import_repository_factory():
    for module in (llm_analyzer, rule_engine):
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "from app.core.repository_factory import get_repository_for_user" in source


# ── Runtime: rule_engine.evaluate_node ──────────────────────────────────────


def test_evaluate_node_routes_through_repo(fake_cp_repo, monkeypatch):
    repository, factory_calls = fake_cp_repo
    repository.nodes["7"] = [
        {"node_id": "topic:intro", "status": "in_progress", "interaction_count": 5,
         "llm_verified": 0, "last_quiz_score": None, "code_task_passed": 0,
         "classroom_progress_pct": 0.0}
    ]
    monkeypatch.setattr("db.get_recent_quizzes", lambda uid, limit: [])
    monkeypatch.setattr("db.get_user_stats", lambda uid: {})
    monkeypatch.setattr("db.get_recent_classrooms", lambda uid, limit: [])

    result = rule_engine.evaluate_node("7", "topic:intro")

    assert factory_calls[0] == ("7", "course_progress")
    assert ("get_learning_path_node", "7", "topic:intro") in repository.calls
    assert result.node_id == "topic:intro"


def test_reevaluate_all_nodes_routes_through_repo(fake_cp_repo, monkeypatch):
    repository, factory_calls = fake_cp_repo
    repository.nodes["7"] = [
        {"node_id": "topic:a", "status": "in_progress", "interaction_count": 0,
         "llm_verified": 0, "last_quiz_score": None, "code_task_passed": 0,
         "classroom_progress_pct": 0.0},
        {"node_id": "topic:b", "status": "locked", "interaction_count": 0,
         "llm_verified": 0, "last_quiz_score": None, "code_task_passed": 0,
         "classroom_progress_pct": 0.0},
    ]
    monkeypatch.setattr("db.get_recent_quizzes", lambda uid, limit: [])
    monkeypatch.setattr("db.get_user_stats", lambda uid: {})
    monkeypatch.setattr("db.get_recent_classrooms", lambda uid, limit: [])

    results = rule_engine.reevaluate_all_nodes("7")

    method_names = [c[0] for c in repository.calls]
    assert "get_learning_path_nodes" in method_names
    # Each node triggers 3 get_learning_path_node calls (evaluate_node, _get_node_study_stats, _apply_result)
    assert method_names.count("get_learning_path_node") == 6
    assert method_names.count("save_learning_path_node") == 2
    assert len(results) == 2


def test_on_quiz_submitted_routes_through_repo(fake_cp_repo, monkeypatch):
    repository, factory_calls = fake_cp_repo
    repository.nodes["7"] = [
        {"node_id": "topic:myquiz", "status": "in_progress", "interaction_count": 0,
         "llm_verified": 0, "last_quiz_score": None, "code_task_passed": 0,
         "classroom_progress_pct": 0.0}
    ]
    monkeypatch.setattr("db.get_recent_quizzes", lambda uid, limit: [])
    monkeypatch.setattr("db.get_user_stats", lambda uid: {})
    monkeypatch.setattr("db.get_recent_classrooms", lambda uid, limit: [])

    result = rule_engine.on_quiz_submitted("7", "my_quiz", 80.0, 100.0)

    assert factory_calls[0] == ("7", "course_progress")
    method_names = [c[0] for c in repository.calls]
    assert "get_learning_path_node" in method_names
    assert "save_learning_path_node" in method_names
    assert result is not None


# ── Runtime: llm_analyzer.apply_llm_analysis ────────────────────────────────


def test_apply_llm_analysis_routes_through_repo(fake_cp_repo, monkeypatch):
    repository, factory_calls = fake_cp_repo
    repository.nodes["7"] = [
        {"node_id": "topic:recursion", "node_topic": "递归", "status": "in_progress",
         "mastery_score": 50.0, "rule_verified": 0, "llm_verified": 0}
    ]
    analysis = llm_analyzer.LLMNodeAnalysis(
        node_id="topic:recursion",
        understood=True,
        confidence=0.85,
        reasoning="good",
        evidence_quotes=[],
        suggested_action="verify",
        recommend_quiz=True,
    )

    result = llm_analyzer.apply_llm_analysis("7", analysis)

    assert factory_calls[0] == ("7", "course_progress")
    method_names = [c[0] for c in repository.calls]
    assert "get_learning_path_node" in method_names
    assert "save_learning_path_node" in method_names
    assert result is True
    # Status should be "mastered" because rule_verified=0 + confidence >= 0.8
    saved_call = next(c for c in repository.calls if c[0] == "save_learning_path_node")
    assert saved_call[2]["status"] == "mastered"


def test_apply_llm_analysis_returns_false_for_missing_node(fake_cp_repo):
    repository, factory_calls = fake_cp_repo
    analysis = llm_analyzer.LLMNodeAnalysis(
        node_id="topic:missing",
        understood=True, confidence=0.9, reasoning="",
        evidence_quotes=[], suggested_action="", recommend_quiz=False,
    )
    result = llm_analyzer.apply_llm_analysis("7", analysis)
    assert result is False
    method_names = [c[0] for c in repository.calls]
    assert "get_learning_path_node" in method_names
    assert "save_learning_path_node" not in method_names


# ── Routing consistency ──────────────────────────────────────────────────────


def test_factory_called_with_course_progress_type_for_both(fake_cp_repo, monkeypatch):
    repository, factory_calls = fake_cp_repo
    monkeypatch.setattr("db.get_recent_quizzes", lambda uid, limit: [])
    monkeypatch.setattr("db.get_user_stats", lambda uid: {})
    monkeypatch.setattr("db.get_recent_classrooms", lambda uid, limit: [])

    # rule_engine path
    repository.nodes["7"] = []
    rule_engine.evaluate_node("7", "topic:x")

    # llm_analyzer path
    repository.nodes["8"] = [
        {"node_id": "topic:y", "node_topic": "y", "status": "in_progress",
         "mastery_score": 0.0, "rule_verified": 0, "llm_verified": 0}
    ]
    analysis = llm_analyzer.LLMNodeAnalysis(
        node_id="topic:y", understood=False, confidence=0.0,
        reasoning="", evidence_quotes=[],
        suggested_action="", recommend_quiz=False,
    )
    llm_analyzer.apply_llm_analysis("8", analysis)

    assert all(rt == "course_progress" for _, rt in factory_calls)
