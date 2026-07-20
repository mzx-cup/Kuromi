from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api import profile as profile_api


class FakeChatRepository:
    def __init__(self, memories: list | None = None, error: Exception | None = None):
        self.memories = memories or []
        self.error = error
        self.calls = []

    def get_memories(
        self, user_id: str, memory_type: str | None = None, limit: int = 20
    ) -> list:
        self.calls.append((user_id, memory_type, limit))
        if self.error:
            raise self.error
        return self.memories


@pytest.mark.asyncio
async def test_get_profile_reads_memories_through_chat_repository(monkeypatch):
    memories = [{"memory_type": "fact", "content": "喜欢 Python"}]
    repository = FakeChatRepository(memories)
    factory_calls = []

    def fake_factory(user_id: str, repository_type: str):
        factory_calls.append((user_id, repository_type))
        return repository

    monkeypatch.setattr(
        profile_api, "get_repository_for_user", fake_factory, raising=False
    )
    monkeypatch.setattr(
        profile_api,
        "aggregate_profile",
        lambda received: {"memory_count": len(received)},
    )

    result = await profile_api.get_profile("u1")

    assert factory_calls == [("u1", "chat")]
    assert repository.calls == [("u1", None, 200)]
    assert result == {
        "success": True,
        "user_id": "u1",
        "profile": {"memory_count": 1},
    }


@pytest.mark.asyncio
async def test_get_profile_preserves_error_response(monkeypatch):
    repository = FakeChatRepository(error=RuntimeError("database unavailable"))
    monkeypatch.setattr(
        profile_api,
        "get_repository_for_user",
        lambda user_id, repository_type: repository,
        raising=False,
    )

    with pytest.raises(HTTPException) as exc_info:
        await profile_api.get_profile("u1")

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "获取画像失败: database unavailable"


def test_profile_api_does_not_import_db_module():
    source_path = Path(profile_api.__file__)
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
