from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.services import course_brainstorm


class FakeCapabilityRepository:
    def __init__(self, profile: dict | None = None, error: Exception | None = None):
        self.profile = profile or {}
        self.error = error
        self.user_ids: list[str] = []

    async def aggregate_profile(self, user_id: str) -> dict:
        self.user_ids.append(user_id)
        if self.error:
            raise self.error
        return self.profile


@pytest.mark.asyncio
async def test_load_portrait_uses_capability_repository(monkeypatch):
    repo = FakeCapabilityRepository(
        {
            "knowledge_base": {"Python": 0.8, "SQL": 0.2},
            "code_skill": {"Python": 0.7, "SQL": 0.3},
            "cognitive_style": {"preferred_modality": "visual", "depth": "deep"},
            "focus_level": {"avg_session_minutes": 50, "streak_days": 4},
            "learning_goals": [
                {
                    "id": 1,
                    "title": "成为后端工程师",
                    "progress": 0.4,
                    "unit": "percent",
                    "deadline": "2026-12-31",
                }
            ],
            "weakness": [{"subject": "SQL", "mastery": 0.2}],
        }
    )
    factory_calls = []

    def fake_factory(user_id: str, repository_type: str):
        factory_calls.append((user_id, repository_type))
        return repo

    monkeypatch.setattr(
        course_brainstorm, "get_repository_for_user", fake_factory, raising=False
    )

    portrait = await course_brainstorm._load_portrait("7")

    assert factory_calls == [("7", "capability")]
    assert repo.user_ids == ["7"]
    assert portrait["knowledge_mastery"]["overall"] == pytest.approx(0.5)
    assert portrait["knowledge_mastery"]["topics"] == [
        {"name": "Python", "level": 0.8},
        {"name": "SQL", "level": 0.2},
    ]
    assert portrait["code_skill"] == {
        "level": "intermediate",
        "strong_areas": ["Python"],
        "weak_areas": ["SQL"],
    }
    assert portrait["cognitive_style"]["type"] == "视觉型"
    assert portrait["learning_goal"]["current"] == "成为后端工程师"
    assert portrait["weakness"]["areas"] == ["SQL"]
    assert portrait["focus_level"]["current"] == "高专注"


@pytest.mark.asyncio
async def test_load_portrait_returns_empty_for_missing_student_id(monkeypatch):
    def unexpected_factory(*args, **kwargs):
        raise AssertionError("factory should not be called")

    monkeypatch.setattr(
        course_brainstorm, "get_repository_for_user", unexpected_factory, raising=False
    )

    assert await course_brainstorm._load_portrait("") == {}


@pytest.mark.asyncio
async def test_load_portrait_returns_empty_when_repository_fails(monkeypatch):
    repo = FakeCapabilityRepository(error=RuntimeError("database unavailable"))
    monkeypatch.setattr(
        course_brainstorm,
        "get_repository_for_user",
        lambda user_id, repository_type: repo,
        raising=False,
    )

    assert await course_brainstorm._load_portrait("7") == {}


def test_course_brainstorm_does_not_import_db_module():
    source_path = Path(course_brainstorm.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    db_imports = [
        node
        for node in ast.walk(tree)
        if (isinstance(node, ast.ImportFrom) and node.module == "db")
        or (
            isinstance(node, ast.Import)
            and any(alias.name == "db" for alias in node.names)
        )
    ]

    assert db_imports == []
