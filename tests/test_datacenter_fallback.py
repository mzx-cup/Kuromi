"""Datacenter dashboard fallback gate (Phase 1.3).

When a user has no learning data, _build_dashboard calls
_build_fallback_dashboard which used to always return hardcoded
fake data (Python 基础 78%, etc.). This was misleading: real users
saw synthetic data and assumed it was theirs.

Improvement (not rewrite): the existing function now checks
ALLOW_DEMO_LOGIN; when false (default / production), raises 404.
When true (dev / demo mode), keeps the original behavior including
the ``_fallback: True`` marker the frontend can detect.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api import datacenter


def test_fallback_returns_404_when_demo_disabled(monkeypatch):
    """Production default: ALLOW_DEMO_LOGIN=false → 404, no fake data."""
    monkeypatch.delenv("ALLOW_DEMO_LOGIN", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        datacenter._build_fallback_dashboard(user_id=999, range_key="30d")

    assert exc_info.value.status_code == 404
    assert "演示模式已关闭" in str(exc_info.value.detail)


def test_fallback_returns_demo_data_when_enabled(monkeypatch):
    """Dev mode: ALLOW_DEMO_LOGIN=true → keep original fake-data behavior
    with ``_fallback: True`` marker so frontend can identify it."""
    monkeypatch.setenv("ALLOW_DEMO_LOGIN", "true")

    result = datacenter._build_fallback_dashboard(user_id=42, range_key="7d")

    # The original signature: returns dict with success flag and demo marker
    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["_fallback"] is True
    assert result["userId"] == 42
    assert result["range"] == "7d"
    # Original demo data structure preserved
    assert "courseProgress" in result
    assert "radar" in result
    assert "timeline" in result
    assert "heatmap" in result
    # 4 hardcoded demo courses preserved
    course_names = [c["name"] for c in result["courseProgress"]]
    assert "Python 基础" in course_names
    assert "数据分析" in course_names


def test_fallback_accepts_truthy_env_values(monkeypatch):
    """ALLOW_DEMO_LOGIN accepts true/1/yes (case-insensitive)."""
    for truthy in ("true", "TRUE", "True", "1", "yes", "YES"):
        monkeypatch.setenv("ALLOW_DEMO_LOGIN", truthy)

        result = datacenter._build_fallback_dashboard(user_id=1, range_key="30d")

        assert result["_fallback"] is True, f"truthy={truthy} should enable demo"


def test_fallback_rejects_falsy_env_values(monkeypatch):
    """ALLOW_DEMO_LOGIN rejects anything other than true/1/yes."""
    for falsy in ("false", "0", "no", "off", "", "anything-else"):
        monkeypatch.setenv("ALLOW_DEMO_LOGIN", falsy)

        with pytest.raises(HTTPException) as exc_info:
            datacenter._build_fallback_dashboard(user_id=1, range_key="30d")

        assert exc_info.value.status_code == 404, f"falsy={falsy} should 404"


def test_fallback_original_demo_courses_unchanged(monkeypatch):
    """Regression: the actual demo data must not be touched — only the gate
    was added. Verifies we improved rather than redesigned."""
    monkeypatch.setenv("ALLOW_DEMO_LOGIN", "true")

    result = datacenter._build_fallback_dashboard(user_id=42, range_key="30d")

    # 6-dimension radar preserved exactly
    radar_dims = result["radar"]["dimensions"]
    radar_names = [d["name"] for d in radar_dims]
    assert "知识掌握" in radar_names
    assert "代码能力" in radar_names
    assert "专注水平" in radar_names
    # 4-courses with emojis preserved
    icons = {c["icon"] for c in result["courseProgress"]}
    assert icons == {"🐍", "📊", "🤖", "🧮"}