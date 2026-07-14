"""Learning path API uses CourseProgressRepository (Task C3).

Verifies:
- Static AST guard: ``database.get_learning_path*`` / ``database.save_learning_path*``
  / ``database.sync_path_to_nodes`` / ``database.save_learning_path_node`` calls
  are absent from ``app/api/learning_path.py`` (only ``database.get_user_profile``
  remains, which has no Repository surface yet)
- The module imports the factory and routes all graph ops through it
- Runtime tests using a fake ``CourseProgressRepository`` confirm the
  ``_merge_node_states_into_path`` helper, ``update_learning_path_nodes``
  and ``get_learning_path_nodes`` route through the repo
"""
from __future__ import annotations

import ast
import asyncio
from pathlib import Path

import pytest

from app.api import learning_path as lp_api


# ── Fake repository ──────────────────────────────────────────────────────────


class FakeCourseProgressRepository:
    def __init__(self):
        self.calls = []
        self.graphs = {}
        # Store under whatever key the API code passes (raw int user_id)
        self.nodes = {}
        self.daily_routes = {}

    def get_learning_path_graph(self, user_id):
        self.calls.append(("get_learning_path_graph", user_id))
        return self.graphs.get(user_id)

    def save_learning_path_graph(self, user_id, path_json, reasoning=None,
                                 data_sources=None, confidence=0.0):
        self.calls.append(("save_learning_path_graph", user_id, path_json,
                           reasoning, data_sources, confidence))
        self.graphs[user_id] = {
            "path_json": path_json,
            "reasoning": reasoning,
            "data_sources": data_sources,
            "confidence": confidence,
            "generated_at": "2026-07-14T00:00:00",
        }

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
                bucket[i] = node_data
                return True
        bucket.append(node_data)
        return True

    def sync_path_to_nodes(self, user_id, path_json):
        self.calls.append(("sync_path_to_nodes", user_id, path_json))
        return 0

    def get_daily_route(self, user_id, route_date):
        self.calls.append(("get_daily_route", user_id, route_date))
        return self.daily_routes.get((user_id, route_date))

    def save_daily_route(self, user_id, route_date, tasks, completed=None):
        self.calls.append(("save_daily_route", user_id, route_date, tasks, completed))
        self.daily_routes[(user_id, route_date)] = {
            "tasks_json": tasks,
            "completed_json": completed or [],
        }


@pytest.fixture
def fake_cp_repo(monkeypatch):
    repository = FakeCourseProgressRepository()
    factory_calls = []

    def factory(user_id: str, repository_type: str):
        factory_calls.append((user_id, repository_type))
        return repository

    monkeypatch.setattr(lp_api, "get_repository_for_user", factory, raising=False)
    return repository, factory_calls


# ── Static AST guard ─────────────────────────────────────────────────────────


def _collect_call_owners(tree):
    """Collect every ``<name>.<attr>(...)`` invocation in the AST.

    Returns a list of ``(lineno, owner_name_or_None, attr_name)``. Skips
    attribute calls on string/numeric constants (e.g. ``"x".upper()``).
    """
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            if isinstance(owner, ast.Name):
                calls.append((node.lineno, owner.id, node.func.attr))
    return calls


def test_learning_path_does_not_call_migrated_db_helpers():
    """All migrated graph-op helpers must route through CourseProgressRepository."""
    source_path = Path(lp_api.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    forbidden = {
        "get_learning_path", "get_learning_path_nodes", "get_learning_path_node",
        "save_learning_path", "save_learning_path_node", "sync_path_to_nodes",
        "get_daily_route", "save_daily_route",
    }

    violations = []
    for lineno, owner, attr in _collect_call_owners(tree):
        if owner == "database" and attr in forbidden:
            violations.append((lineno, f"database.{attr}"))
    assert violations == [], f"Forbidden db.py calls remain: {violations}"


def test_learning_path_imports_repository_factory():
    source = Path(lp_api.__file__).read_text(encoding="utf-8")
    assert "from app.core.repository_factory import get_repository_for_user" in source


def test_learning_path_only_imports_infra_symbols_from_db():
    """``from db import`` must be only the infra surface (no migrated helpers)."""
    tree = ast.parse(Path(lp_api.__file__).read_text(encoding="utf-8"))
    allowed = {"get_db", "_is_sqlite", "load_local_storage", "save_local_storage", "_is_mysql"}

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "db":
            for alias in node.names:
                if alias.name not in allowed:
                    violations.append((node.lineno, alias.name))
    assert violations == [], f"Forbidden db imports: {violations}"


# ── Runtime: _merge_node_states_into_path ────────────────────────────────────


def test_merge_node_states_routes_through_repo(fake_cp_repo):
    repository, factory_calls = fake_cp_repo
    # API code passes raw int user_id to repo method
    repository.nodes[7] = [
        {"node_id": "topic:intro", "status": "completed", "mastery_score": 0.95,
         "completion_source": "rule", "rule_verified": 1, "llm_verified": 0},
    ]

    path = [
        {"topic": "intro", "id": "topic:intro", "status": "in_progress",
         "children": [{"topic": "sub", "id": "topic:intro:sub", "status": "locked"}]},
    ]

    lp_api._merge_node_states_into_path(7, path)

    assert factory_calls == [("7", "course_progress")]
    assert ("get_learning_path_nodes", 7) in repository.calls
    # node-tracker state overrides LLM-generated state
    assert path[0]["status"] == "completed"
    assert path[0]["mastery_score"] == 0.95


def test_merge_node_states_handles_empty_nodes(fake_cp_repo):
    repository, factory_calls = fake_cp_repo
    path = [{"topic": "x", "id": "topic:x", "status": "locked"}]
    lp_api._merge_node_states_into_path("u1", path)
    assert factory_calls == [("u1", "course_progress")]
    assert path[0]["status"] == "locked"  # unchanged


# ── Runtime: update_learning_path_nodes ──────────────────────────────────────


def test_update_nodes_routes_through_repo(fake_cp_repo):
    repository, factory_calls = fake_cp_repo

    item = lp_api.NodeUpdateItem(
        node_id="topic:intro", status="completed", mastery_score=0.8,
        rule_verified=True, llm_verified=False,
        completion_source="rule", evidence_json={"k": "v"},
    )
    request = lp_api.BatchUpdateNodesRequest(userId=7, nodes=[item])

    result = asyncio.run(lp_api.update_learning_path_nodes(request))

    assert factory_calls == [("7", "course_progress")]
    call_names = [c[0] for c in repository.calls]
    assert "get_learning_path_node" in call_names
    assert "save_learning_path_node" in call_names
    assert result.success is True
    assert result.nodes == [{"node_id": "topic:intro"}]
    assert result.evaluated_count == 1
    assert result.changed_count == 1  # old_status None -> completed = change


def test_update_nodes_no_change(fake_cp_repo):
    repository, factory_calls = fake_cp_repo
    # Pre-populate with matching status (under int 7, matching request.userId)
    repository.nodes.setdefault(7, []).append(
        {"node_id": "topic:intro", "status": "completed"}
    )

    item = lp_api.NodeUpdateItem(node_id="topic:intro", status="completed")
    request = lp_api.BatchUpdateNodesRequest(userId=7, nodes=[item])

    result = asyncio.run(lp_api.update_learning_path_nodes(request))
    assert result.changed_count == 0


# ── Runtime: get_learning_path_nodes ─────────────────────────────────────────


def test_get_nodes_routes_through_repo(fake_cp_repo):
    repository, factory_calls = fake_cp_repo
    repository.nodes["u1"] = [
        {"node_id": "a", "status": "completed"},
        {"node_id": "b", "status": "locked"},
    ]

    result = asyncio.run(lp_api.get_learning_path_nodes("u1"))

    assert factory_calls == [("u1", "course_progress")]
    assert ("get_learning_path_nodes", "u1") in repository.calls
    assert len(result.nodes) == 2


# ── Runtime: get_current_learning_path ───────────────────────────────────────


def test_get_current_routes_through_repo(fake_cp_repo, monkeypatch):
    repository, factory_calls = fake_cp_repo
    # No graph stored -> returns empty path; we still want to verify routing
    monkeypatch.setattr(
        "db.get_user_profile", lambda uid: {"profile_json": '{"knowledgeBase": "零基础入门", "codeSkill": "编程新手"}'}
    )

    result = asyncio.run(lp_api.get_current_learning_path(7))

    assert factory_calls == [("7", "course_progress")]
    assert ("get_learning_path_graph", 7) in repository.calls
    assert result.success is True
    assert result.path == []


def test_get_current_returns_stored_path(fake_cp_repo, monkeypatch):
    repository, factory_calls = fake_cp_repo
    repository.graphs[7] = {
        "path_json": [{"topic": "intro", "status": "in_progress"}],
        "reasoning": "test",
        "data_sources": ["local"],
        "generated_at": "2026-07-14T00:00:00",
        "confidence": 0.8,
    }
    monkeypatch.setattr(
        "db.get_user_profile", lambda uid: {"profile_json": '{"knowledgeBase": "零基础入门", "codeSkill": "编程新手"}'}
    )

    result = asyncio.run(lp_api.get_current_learning_path(7))

    assert result.path == [{"topic": "intro", "status": "in_progress"}]
    assert result.reasoning == "test"
    assert result.confidence == 0.8


# ── Routing consistency ──────────────────────────────────────────────────────


def test_factory_called_with_course_progress_type_only(fake_cp_repo):
    """All factory calls in this module must ask for ``course_progress`` repos."""
    repository, factory_calls = fake_cp_repo
    asyncio.run(lp_api.get_learning_path_nodes("u1"))
    asyncio.run(lp_api.update_learning_path_nodes(
        lp_api.BatchUpdateNodesRequest(userId=2, nodes=[])
    ))
    assert all(rt == "course_progress" for _, rt in factory_calls)
