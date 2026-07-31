# -*- coding: utf-8 -*-
"""P1 Task 21: 教师/学生用户隔离测试.

覆盖:
  1. 无 token → 401
  2. 无效 token → 401
  3. 学生 A token 想读学生 B 数据 → 403
  4. 学生 A token 读自己数据 → 200
  5. 教师 token 读任意学生数据 → 200
  6. 学生 token 试图访问教师端点 → 403
  7. 教师 token 访问教师端点 → 200
  8. 无 token 访问教师端点 → 401

不依赖外部服务, 用 TestClient + 临时 JWT 跑.
"""
import time
import uuid
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

from main import app  # noqa: E402

# 与 app.api.auth 一致: 启动期已校验的 JWT_SECRET (tests/conftest.py 已 setdefault 60 字节).
from app.api.auth import JWT_SECRET, JWT_ALGORITHM  # noqa: E402

client = TestClient(app)


def _make_jwt(uid: str, role: str = "student", username: str | None = None) -> str:
    """构造一个测试用 JWT."""
    payload = {
        "uid": uid,
        "username": username or uid,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ============================================================
# 1. /api/profile/{user_id}/mastery-diff 隔离
# ============================================================


class TestMasteryDiffIsolation:
    def test_no_token_returns_401(self):
        r = client.get("/api/profile/student_a/mastery-diff")
        assert r.status_code == 401, r.text

    def test_invalid_token_returns_401(self):
        r = client.get(
            "/api/profile/student_a/mastery-diff",
            headers={"Authorization": "Bearer not-a-real-jwt"},
        )
        assert r.status_code == 401, r.text

    def test_student_a_cannot_read_student_b(self):
        token_a = _make_jwt("student_a", role="student")
        r = client.get(
            "/api/profile/student_b/mastery-diff",
            headers=_bearer(token_a),
        )
        assert r.status_code == 403, r.text

    def test_student_can_read_own(self):
        token_a = _make_jwt("student_a", role="student")
        r = client.get(
            "/api/profile/student_a/mastery-diff",
            headers=_bearer(token_a),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["user_id"] == "student_a"
        assert "items" in body

    def test_teacher_can_read_any_student(self):
        token_t = _make_jwt("teacher_1", role="teacher")
        r = client.get(
            "/api/profile/student_a/mastery-diff",
            headers=_bearer(token_t),
        )
        assert r.status_code == 200, r.text
        assert r.json()["user_id"] == "student_a"

    def test_admin_can_read_any_student(self):
        token_admin = _make_jwt("admin_1", role="admin")
        r = client.get(
            "/api/profile/student_a/mastery-diff",
            headers=_bearer(token_admin),
        )
        assert r.status_code == 200, r.text


# ============================================================
# 2. /api/profile/{user_id}/recommendations 隔离
# ============================================================


class TestRecommendationsIsolation:
    def test_no_token_returns_401(self):
        r = client.get("/api/profile/student_a/recommendations")
        assert r.status_code == 401, r.text

    def test_student_b_cannot_read_student_a(self):
        token_b = _make_jwt("student_b", role="student")
        r = client.get(
            "/api/profile/student_a/recommendations",
            headers=_bearer(token_b),
        )
        assert r.status_code == 403, r.text

    def test_student_can_read_own_recommendations(self):
        token_a = _make_jwt("student_a", role="student")
        r = client.get(
            "/api/profile/student_a/recommendations",
            headers=_bearer(token_a),
        )
        assert r.status_code == 200, r.text
        assert "recommendations" in r.json()

    def test_teacher_can_read_any_recommendations(self):
        token_t = _make_jwt("teacher_1", role="teacher")
        r = client.get(
            "/api/profile/student_a/recommendations",
            headers=_bearer(token_t),
        )
        assert r.status_code == 200, r.text


# ============================================================
# 3. /api/teacher/dashboard/observation 仅教师
# ============================================================


class TestTeacherEndpointIsolation:
    def test_no_token_returns_401(self):
        r = client.get("/api/teacher/dashboard/observation")
        assert r.status_code == 401, r.text

    def test_student_token_returns_403(self):
        token_s = _make_jwt("student_a", role="student")
        r = client.get(
            "/api/teacher/dashboard/observation",
            headers=_bearer(token_s),
        )
        assert r.status_code == 403, r.text

    def test_teacher_token_returns_200(self):
        token_t = _make_jwt("teacher_1", role="teacher")
        r = client.get(
            "/api/teacher/dashboard/observation",
            headers=_bearer(token_t),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "observations" in body
        assert isinstance(body["observations"], list)

    def test_admin_token_returns_200(self):
        token_admin = _make_jwt("admin_1", role="admin")
        r = client.get(
            "/api/teacher/dashboard/observation",
            headers=_bearer(token_admin),
        )
        assert r.status_code == 200, r.text


# ============================================================
# 4. 边界: username 匹配也算本人
# ============================================================


class TestUsernameMatch:
    def test_match_by_username_in_path(self):
        """路径用 username 而非 uid 时, 也能匹配."""
        # 注册一个 username=user_x, uid=42 的 token
        token = _make_jwt(uid="42", username="user_x", role="student")
        # 用 username 访问, 应该放行
        r = client.get(
            "/api/profile/user_x/recommendations",
            headers=_bearer(token),
        )
        assert r.status_code == 200, r.text
