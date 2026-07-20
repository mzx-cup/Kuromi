"""Auth API uses UserRepository (Task B8).

Verifies:
- login, register, /me, and _ensure_demo_accounts all use ``user_repo.get_by_username``
- The factory routes to a "user" repository, not legacy ``db.get_user_by_username``
- API still works correctly: login returns token + user info, /me returns user info
- The ``user`` module only imports infra symbols (``get_db`` / ``_is_sqlite`` /
  ``load_local_storage`` / ``save_local_storage``) and ``UserRepository`` factory
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.api import auth as auth_api


class FakeUserRepository:
    def __init__(self):
        self.calls = []
        self.users = {}

    def get_by_username(self, username):
        self.calls.append(("get_by_username", username))
        return self.users.get(username)

    def create_user(self, username, password_hash, preferred_language="zh-CN"):
        self.calls.append(("create_user", username, password_hash, preferred_language))
        user_id = len(self.users) + 1
        record = {
            "id": user_id,
            "username": username,
            "password": password_hash,
            "role": "student",
            "display_name": username,
            "nickname": username,
            "avatar": "",
            "preferred_language": preferred_language,
        }
        self.users[username] = record
        return user_id

    def record_login(self, user_id, ip="", user_agent=""):
        self.calls.append(("record_login", user_id, ip, user_agent))
        return None

    def get_login_history(self, user_id):
        self.calls.append(("get_login_history", user_id))
        return []


@pytest.fixture
def user_repository(monkeypatch):
    repository = FakeUserRepository()
    factory_calls = []

    def factory(user_id: str, repository_type: str):
        factory_calls.append((user_id, repository_type))
        return repository

    monkeypatch.setattr(
        auth_api, "get_repository_for_user", factory, raising=False
    )
    return repository, factory_calls


def _install_demo_users(repository, usernames):
    """Pre-populate the fake repo with demo accounts (``_ensure_demo_accounts``
    would otherwise create them via raw INSERT)."""
    for u in usernames:
        repository.users[u] = {
            "id": hash(u) % 1000,
            "username": u,
            "password": auth_api._hash_password("123456"),
            "role": {"teacher": "teacher", "student": "student", "admin": "admin"}.get(u, "student"),
            "display_name": u,
            "nickname": u,
            "avatar": "",
        }


def test_login_uses_user_repository(user_repository):
    repository, factory_calls = user_repository
    _install_demo_users(repository, ["teacher"])
    request = auth_api.LoginRequest(username="teacher", password="123456")

    result = auth_api.login(request)

    assert factory_calls == [("teacher", "user")]
    assert repository.calls[0] == ("get_by_username", "teacher")
    assert "token" in result
    assert result["user"]["username"] == "teacher"
    assert result["user"]["role"] == "teacher"


def test_login_wrong_password_returns_401(user_repository):
    repository, factory_calls = user_repository
    _install_demo_users(repository, ["teacher"])
    request = auth_api.LoginRequest(username="teacher", password="wrong")

    with pytest.raises(Exception) as exc_info:
        auth_api.login(request)
    assert "401" in str(exc_info.value) or "用户名或密码错误" in str(exc_info.value)


def test_login_missing_user_returns_401(user_repository):
    repository, factory_calls = user_repository
    request = auth_api.LoginRequest(username="ghost", password="123456")

    with pytest.raises(Exception) as exc_info:
        auth_api.login(request)
    assert "401" in str(exc_info.value) or "用户名或密码错误" in str(exc_info.value)


def test_register_uses_user_repository_for_existing_check(user_repository):
    repository, factory_calls = user_repository
    _install_demo_users(repository, ["teacher"])
    request = auth_api.RegisterRequest(
        username="teacher", password="123456", display_name="dup"
    )

    with pytest.raises(Exception) as exc_info:
        auth_api.register(request)
    assert "409" in str(exc_info.value) or "已存在" in str(exc_info.value)
    assert factory_calls == [("teacher", "user")]
    assert ("get_by_username", "teacher") in repository.calls


def test_get_me_uses_user_repository(user_repository):
    repository, factory_calls = user_repository
    _install_demo_users(repository, ["teacher"])

    token = auth_api.create_jwt(repository.users["teacher"])
    from fastapi import Request
    import asyncio

    scope = {
        "type": "http",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
    }
    request = Request(scope)

    result = asyncio.run(_call_get_me(request))

    assert factory_calls == [("teacher", "user")]
    assert ("get_by_username", "teacher") in repository.calls
    assert result["user"]["username"] == "teacher"


async def _call_get_me(request):
    """Wrap the sync ``get_me`` in a coroutine for asyncio.run."""
    return auth_api.get_me(request)


def test_ensure_demo_accounts_uses_user_repository(user_repository, monkeypatch):
    repository, factory_calls = user_repository
    monkeypatch.setattr(auth_api, "_ensure_user_table", lambda: None)
    monkeypatch.setattr(auth_api, "ALLOW_DEMO_LOGIN", True)

    auth_api._ensure_demo_accounts()

    # Should have queried the repo for each demo username (teacher, student, admin)
    queries = [c for c in repository.calls if c[0] == "get_by_username"]
    assert ("get_by_username", "teacher") in queries
    assert ("get_by_username", "student") in queries
    assert ("get_by_username", "admin") in queries


def test_ensure_demo_accounts_skipped_when_demo_login_disabled(user_repository, monkeypatch):
    """Phase 1.1: when ALLOW_DEMO_LOGIN=false, ``_ensure_demo_accounts`` is a no-op.

    This is the safety gate that prevents production deployments from silently
    creating teacher/student/admin (123456) accounts at module import time.
    """
    repository, _ = user_repository
    monkeypatch.setattr(auth_api, "ALLOW_DEMO_LOGIN", False)

    auth_api._ensure_demo_accounts()

    # No repo calls should have been made
    assert repository.calls == []


def test_auth_api_only_imports_infra_and_factory_from_db():
    """The auth API must not import ``get_user_by_username`` from db."""
    source_path = Path(auth_api.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "db":
            imported = {alias.name for alias in node.names}
            # Allowed infra symbols
            allowed = {"get_db", "_is_sqlite", "load_local_storage", "save_local_storage", "_is_mysql"}
            illegal = imported - allowed
            if illegal:
                violations.append((node.lineno, imported))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "db":
                    violations.append((node.lineno, {"db (as import)"}))

    assert violations == [], f"Forbidden db imports: {violations}"


def test_auth_api_uses_repository_factory():
    """auth.py should call ``get_repository_for_user`` (not legacy db helpers)."""
    source = Path(auth_api.__file__).read_text(encoding="utf-8")
    assert "get_repository_for_user" in source
    # Should NOT contain db.get_user_by_username (the migrated function)
    assert "get_user_by_username" not in source or "_ensure_demo_accounts" in source
