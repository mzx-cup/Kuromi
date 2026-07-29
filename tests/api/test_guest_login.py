import re

from fastapi.testclient import TestClient

from main import app  # noqa: E402


client = TestClient(app)


def test_guest_login_returns_predictable_username():
    """游客登录 username 应该是 guest_<8 位 uuid4 hex> 格式，可预测。"""
    response = client.post("/api/login/guest")

    assert response.status_code == 200
    body = response.json()
    assert re.fullmatch(r"guest_[0-9a-f]{8}", body["username"]), (
        f"unexpected username format: {body['username']}"
    )


def test_guest_login_exposes_both_user_id_aliases():
    """响应里必须有 userId（向后兼容，前端依赖）+ user_id（snake_case alias），
    且两值相等。"""
    response = client.post("/api/login/guest")

    assert response.status_code == 200
    body = response.json()
    assert "userId" in body
    assert "user_id" in body
    assert body["userId"] == body["user_id"]


def test_guest_login_two_calls_have_different_identifiers():
    response_one = client.post("/api/login/guest")
    response_two = client.post("/api/login/guest")

    assert response_one.status_code == 200
    assert response_two.status_code == 200
    # username 每次都是新生成的 uuid4 hex
    assert response_one.json()["username"] != response_two.json()["username"]
    # DB 主键也不同
    assert response_one.json()["user_id"] != response_two.json()["user_id"]
