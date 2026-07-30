"""Tests for teacher AI suggestions API (M4.1).

验证:
  - GET /api/teacher/ai-suggestions 返回建议列表
  - POST /api/teacher/suggestion/{id}/act 返回 act 结果
"""
from __future__ import annotations

import pytest


def test_get_ai_suggestions_returns_list():
    """/api/teacher/ai-suggestions 必须返回 suggestions 列表。"""
    from app.api.teacher import router

    # 通过路由直接调用（不依赖 TestClient / DB）
    for route in router.routes:
        if getattr(route, "path", "") == "/api/teacher/ai-suggestions":
            assert route.methods is not None
            assert "GET" in route.methods
            return
    raise AssertionError("route /api/teacher/ai-suggestions not found")


def test_act_on_suggestion_route_exists():
    """/api/teacher/suggestion/{suggestion_id}/act 必须存在。"""
    from app.api.teacher import router

    for route in router.routes:
        path = getattr(route, "path", "")
        if "/suggestion/" in path and path.endswith("/act"):
            assert route.methods is not None
            assert "POST" in route.methods
            return
    raise AssertionError("route /api/teacher/suggestion/{id}/act not found")


def test_ai_suggestions_returns_valid_structure():
    """handler 必须返回 dict 含 'suggestions' 字段。"""
    from app.api.teacher import router
    from fastapi.routing import APIRoute

    # 找到 handler 函数并直接调用（FastAPI 把签名清理过，所以 inspect 后再传 default）
    for route in router.routes:
        if getattr(route, "path", "") == "/api/teacher/ai-suggestions" and isinstance(route, APIRoute):
            # 调起 endpoint，FastAPI inspect 时把 Query default 去掉了
            # 用 route.endpoint 的原始函数签名拿 default
            import inspect

            sig = inspect.signature(route.endpoint)
            kwargs = {}
            for name, param in sig.parameters.items():
                if param.default is inspect.Parameter.empty:
                    kwargs[name] = None  # teacher_id 等可选 header
                else:
                    kwargs[name] = param.default
            result = route.endpoint(**kwargs)
            assert "suggestions" in result
            assert isinstance(result["suggestions"], list)
            return
    raise AssertionError("route not found")


def test_act_on_suggestion_returns_status():
    """act handler 必须返回 acted_at + status 字段。"""
    from app.api.teacher import act_on_suggestion

    result = act_on_suggestion(
        suggestion_id="sg_123",
        payload={"action": "send_to_student", "message": "加油"},
        teacher_id="t_1",
    )
    assert result["suggestion_id"] == "sg_123"
    assert result["action"] == "send_to_student"
    assert result["status"] == "delivered"
    assert "acted_at" in result