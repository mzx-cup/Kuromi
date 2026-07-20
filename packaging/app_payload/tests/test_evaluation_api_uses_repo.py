from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.api import evaluation as evaluation_api


class FakeLearningRepository:
    def __init__(self):
        self.calls = []
        self.evaluation = None
        self.learning_record = None
        self.history = []

    def get_user_evaluation(self, user_id, record_date=None):
        self.calls.append(("get_user_evaluation", user_id, record_date))
        return self.evaluation

    def save_user_evaluation(self, user_id, evaluation):
        self.calls.append(("save_user_evaluation", user_id, evaluation))
        return 1

    def get_learning_record(self, user_id):
        self.calls.append(("get_learning_record", user_id))
        return self.learning_record

    def save_learning_record(self, user_id, record):
        self.calls.append(("save_learning_record", user_id, record))
        return 1

    def get_user_evaluation_history(self, user_id, days=7):
        self.calls.append(("get_user_evaluation_history", user_id, days))
        return self.history


@pytest.fixture
def repository_factory(monkeypatch):
    repository = FakeLearningRepository()
    factory_calls = []

    def factory(user_id: str, repository_type: str):
        factory_calls.append((user_id, repository_type))
        return repository

    monkeypatch.setattr(
        evaluation_api, "get_repository_for_user", factory, raising=False
    )
    return repository, factory_calls


def test_update_evaluation_uses_learning_repository(repository_factory):
    repository, factory_calls = repository_factory
    repository.evaluation = {"eval_json": {"lastStudyDate": "2026-07-13"}}
    repository.learning_record = {
        "interaction_count": 1,
        "code_practice_time": 7,
        "socratic_pass_rate": 0.5,
        "difficulty_level": "intermediate",
        "profile_json": {
            "focus_time_today": 10,
            "flashcards_studied": 2,
            "streak_days": 3,
        },
    }
    request = evaluation_api.UpdateEvaluationRequest(
        userId=7,
        interactionCount=4,
        focusTimeToday=25,
        evalJson={"newMetric": 9},
    )

    result = evaluation_api.update_evaluation(request)

    assert factory_calls == [("7", "learning")]
    assert repository.calls[1] == (
        "save_user_evaluation",
        7,
        {
            "interactionCount": 4,
            "focusTimeToday": 25,
            "lastStudyDate": "2026-07-13",
            "newMetric": 9,
        },
    )
    assert repository.calls[3] == (
        "save_learning_record",
        7,
        {
            "interaction_count": 4,
            "code_practice_time": 7,
            "socratic_pass_rate": 0.5,
            "difficulty_level": "intermediate",
            "profile_json": {
                "focus_time_today": 25,
                "flashcards_studied": 2,
                "streak_days": 3,
            },
        },
    )
    assert result == {"success": True, "message": "评估指标更新成功"}


def test_get_evaluation_uses_learning_repository(repository_factory):
    repository, factory_calls = repository_factory
    repository.evaluation = {
        "interaction_count": 8,
        "socratic_pass_rate": 0.75,
        "difficulty_level": "advanced",
        "code_practice_time": 30,
        "focus_time_today": 20,
        "flashcards_studied": 5,
        "streak_days": 6,
        "eval_json": {"lastStudyDate": "2026-07-13"},
    }
    repository.learning_record = {}

    result = evaluation_api.get_evaluation(7)

    assert factory_calls == [("7", "learning")]
    assert result["success"] is True
    assert result["data"]["interactionCount"] == 8
    assert result["data"]["difficultyLevel"] == "advanced"
    assert result["data"]["lastStudyDate"] == "2026-07-13"


def test_get_evaluation_history_uses_learning_repository(repository_factory):
    repository, factory_calls = repository_factory
    repository.history = [{"record_date": "2026-07-13"}]

    result = evaluation_api.get_evaluation_history(7, days=14)

    assert factory_calls == [("7", "learning")]
    assert repository.calls == [("get_user_evaluation_history", 7, 14)]
    assert result == {
        "success": True,
        "count": 1,
        "data": repository.history,
    }


def test_evaluation_api_does_not_import_db_module():
    source_path = Path(evaluation_api.__file__)
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
