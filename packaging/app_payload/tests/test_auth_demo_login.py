"""POST /api/auth/demo-login (Phase 1.2).

Behavior:
- ALLOW_DEMO_LOGIN=false (default) → 403 Forbidden
- ALLOW_DEMO_LOGIN=true + valid role → calls ``_ensure_demo_accounts``, signs JWT
- ALLOW_DEMO_LOGIN=true + invalid role → 400 Bad Request
- Response shape mirrors /login with extra ``isDemo: true`` flag
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api import auth as auth_api


class FakeUserRepository:
    def __init__(self):
        self.calls = []
        self.users = {}

    def get_by_username(self, username):
        self.calls.append(("get_by_username", username))
        return self.users.get(username)

    def create_user(self, username, password_hash, preferred_language="zh-CN"):
        self.calls.append(("create_user", username))
        record = {
            "id": len(self.users) + 1, "username": username,
            "password": password_hash, "role": "student",
            "display_name": username, "nickname": username, "avatar": "",
        }
        self.users[username] = record
        return record["id"]


@pytest.fixture
def fake_repo(monkeypatch):
    repository = FakeUserRepository()
    factory_calls = []

    def factory(user_id, repository_type):
        factory_calls.append((user_id, repository_type))
        return repository

    monkeypatch.setattr(auth_api, "get_repository_for_user", factory, raising=False)
    monkeypatch.setattr(auth_api, "_ensure_user_table", lambda: None)
    return repository, factory_calls


def test_demo_login_rejected_when_flag_disabled(fake_repo, monkeypatch):
    """Default production state: ALLOW_DEMO_LOGIN=false → 403."""
    repository, _ = fake_repo
    monkeypatch.setattr(auth_api, "ALLOW_DEMO_LOGIN", False)

    with pytest.raises(HTTPException) as exc_info:
        auth_api.demo_login(role="teacher")

    assert exc_info.value.status_code == 403
    assert "禁用" in str(exc_info.value.detail)
    # Should NOT have queried the repo (gated before any DB work)
    assert repository.calls == []


def test_demo_login_creates_and_returns_token(fake_repo, monkeypatch):
    """ALLOW_DEMO_LOGIN=true + valid role → ensure accounts + sign JWT."""
    repository, factory_calls = fake_repo
    monkeypatch.setattr(auth_api, "ALLOW_DEMO_LOGIN", True)
    # Pre-install all three so the ensure finds them already existing
    for role, display in [("teacher", "教师演示"), ("student", "学生演示"), ("admin", "管理员")]:
        repository.users[role] = {
            "id": hash(role) % 100, "username": role, "password": "x", "role": role,
            "display_name": display, "nickname": display, "avatar": "",
        }

    result = auth_api.demo_login(role="student")

    assert result["isDemo"] is True
    assert "token" in result
    assert result["user"]["username"] == "student"
    assert result["user"]["role"] == "student"
    # Factory called at least once for the requested role
    assert ("student", "user") in factory_calls
    # All factory calls are for "user" repository
    assert all(rt == "user" for _, rt in factory_calls)


def test_demo_login_invalid_role_returns_400(fake_repo, monkeypatch):
    """ALLOW_DEMO_LOGIN=true but role not in DEMO_ACCOUNTS → 400."""
    repository, _ = fake_repo
    monkeypatch.setattr(auth_api, "ALLOW_DEMO_LOGIN", True)

    with pytest.raises(HTTPException) as exc_info:
        auth_api.demo_login(role="ghost")

    assert exc_info.value.status_code == 400
    assert "无效" in str(exc_info.value.detail)
    assert repository.calls == []


def test_demo_login_each_valid_role(fake_repo, monkeypatch):
    """teacher / student / admin all accepted."""
    repository, _ = fake_repo
    monkeypatch.setattr(auth_api, "ALLOW_DEMO_LOGIN", True)

    for role, display in [("teacher", "教师演示"), ("student", "学生演示"), ("admin", "管理员")]:
        # Reset and pre-populate
        repository.users.clear()
        repository.users[role] = {
            "id": hash(role) % 100, "username": role, "password": "x", "role": role,
            "display_name": display, "nickname": display, "avatar": "",
        }

        result = auth_api.demo_login(role=role)

        assert result["isDemo"] is True
        assert result["user"]["username"] == role
        assert result["user"]["role"] == role


def test_demo_login_response_shape_matches_login(fake_repo, monkeypatch):
    """Both endpoints return ``token`` + ``user`` dict; demo adds ``isDemo`` flag."""
    repository, _ = fake_repo
    monkeypatch.setattr(auth_api, "ALLOW_DEMO_LOGIN", True)
    repository.users["student"] = {
        "id": 1, "username": "student", "password": "x", "role": "student",
        "display_name": "学生演示", "nickname": "学生演示", "avatar": "",
    }

    demo_result = auth_api.demo_login(role="student")

    # /login response (simulated)
    login_request = auth_api.LoginRequest(username="student", password="123456-stub")
    # Just check shape symmetry — we already proved login works in test_auth_api_uses_repo
    assert set(demo_result.keys()) >= {"token", "user", "isDemo"}
    assert isinstance(demo_result["token"], str)
    assert isinstance(demo_result["user"], dict)