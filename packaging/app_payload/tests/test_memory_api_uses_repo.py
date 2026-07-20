from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.api import memory as memory_api


class FakeChatRepository:
    def __init__(self):
        self.calls = []
        self.memories = [
            {"id": 1, "memory_type": "fact", "content": "喜欢 Python"}
        ]

    def get_memories(
        self, user_id: str, memory_type: str | None = None, limit: int = 20
    ) -> list:
        self.calls.append(("get_memories", user_id, memory_type, limit))
        return self.memories

    def save_memory(self, user_id: str, memory: dict) -> int:
        self.calls.append(("save_memory", user_id, memory))
        return 42

    def update_memory(self, memory_id: int | str, updates: dict) -> None:
        self.calls.append(("update_memory", memory_id, updates))

    def confirm_memory(
        self, memory_id: int | str, confirmed: bool = True
    ) -> None:
        self.calls.append(("confirm_memory", memory_id, confirmed))

    def delete_memory(self, memory_id: int | str) -> None:
        self.calls.append(("delete_memory", memory_id))


@pytest.fixture
def repository_factory(monkeypatch):
    repository = FakeChatRepository()
    factory_calls = []

    def factory(user_id: str, repository_type: str):
        factory_calls.append((user_id, repository_type))
        return repository

    monkeypatch.setattr(
        memory_api, "get_repository_for_user", factory, raising=False
    )
    return repository, factory_calls


def test_get_memories_uses_chat_repository(repository_factory):
    repository, factory_calls = repository_factory

    result = memory_api.get_memories("u1", memory_type="fact", limit=25)

    assert factory_calls == [("u1", "chat")]
    assert repository.calls == [("get_memories", "u1", "fact", 25)]
    assert result == {
        "success": True,
        "count": 1,
        "memories": repository.memories,
    }


def test_create_memory_uses_chat_repository(repository_factory):
    repository, factory_calls = repository_factory
    request = memory_api.CreateMemoryRequest(
        user_id="u1", memory_type="preference", content="偏好图示"
    )

    result = memory_api.create_memory(request)

    assert factory_calls == [("u1", "chat")]
    assert repository.calls == [
        (
            "save_memory",
            "u1",
            {
                "memory_type": "preference",
                "content": "偏好图示",
                "source": "manual",
                "confidence": 0.95,
            },
        )
    ]
    assert result["success"] is True
    assert result["memory_id"] == 42
    assert result["memory"]["id"] == 42


def test_update_memory_content_uses_chat_repository(repository_factory):
    repository, factory_calls = repository_factory

    result = memory_api.update_memory(
        "42", memory_api.UpdateMemoryRequest(content="新内容")
    )

    assert factory_calls == [("42", "chat")]
    assert repository.calls == [("update_memory", 42, {"content": "新内容"})]
    assert result == {"success": True, "memory_id": "42"}


def test_confirm_memory_uses_chat_repository(repository_factory):
    repository, factory_calls = repository_factory

    result = memory_api.confirm_memory(
        "42", memory_api.ConfirmMemoryRequest(confirmed=False)
    )

    assert factory_calls == [("42", "chat")]
    assert repository.calls == [("confirm_memory", 42, False)]
    assert result == {"success": True, "memory_id": "42", "confirmed": False}


def test_delete_memory_uses_chat_repository(repository_factory):
    repository, factory_calls = repository_factory

    result = memory_api.delete_memory("42")

    assert factory_calls == [("42", "chat")]
    assert repository.calls == [("delete_memory", 42)]
    assert result == {"success": True, "memory_id": "42"}


def test_memory_api_only_imports_approved_db_infrastructure():
    source_path = Path(memory_api.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "db"
        for alias in node.names
    }
    imports_db_module = any(
        isinstance(node, ast.Import)
        and any(alias.name == "db" for alias in node.names)
        for node in ast.walk(tree)
    )

    assert imported_names <= {"get_db", "_is_sqlite"}
    assert imports_db_module is False
