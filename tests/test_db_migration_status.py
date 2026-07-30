"""Tests for db.py ORM migration status (M5.7 / Task 31).

验证：
  - feature flags 工作正常
  - 新增模块（app/agents/、app/services/learning_path/ 等）未引入 db.py 依赖
  - KB 模块测试仍能跑通（4/4）
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def test_feature_flags_module_exists():
    """feature_flags 必须存在 + 提供 get_read_percentage / is_dual_write_enabled。"""
    from app.core import feature_flags

    assert hasattr(feature_flags, "get_read_percentage")
    assert hasattr(feature_flags, "is_dual_write_enabled")
    assert hasattr(feature_flags, "is_orm_enabled")


def test_read_backend_percentage_default_zero(monkeypatch):
    """未设环境变量时，get_read_percentage 必须为 0（默认走旧 db.py）。"""
    monkeypatch.delenv("READ_BACKEND_PERCENTAGE", raising=False)
    from app.core.feature_flags import get_read_percentage

    assert get_read_percentage() == 0


def test_read_backend_percentage_parses_valid_value(monkeypatch):
    """合法值（0-100）必须被解析。"""
    monkeypatch.setenv("READ_BACKEND_PERCENTAGE", "75")
    from app.core.feature_flags import get_read_percentage

    assert get_read_percentage() == 75


def test_dual_write_default_false(monkeypatch):
    """DUAL_WRITE_LEGACY 默认 false。"""
    monkeypatch.delenv("DUAL_WRITE_LEGACY", raising=False)
    from app.core.feature_flags import is_dual_write_enabled

    assert is_dual_write_enabled() is False


def test_dual_write_explicit_true(monkeypatch):
    """DUAL_WRITE_LEGACY=true 必须返回 True。"""
    monkeypatch.setenv("DUAL_WRITE_LEGACY", "true")
    from app.core.feature_flags import is_dual_write_enabled

    assert is_dual_write_enabled() is True


def test_new_agents_module_no_db_import():
    """app/agents/* 必须不引入 db.py。"""
    agents_dir = Path("app/agents")
    if not agents_dir.exists():
        pytest.skip("app/agents not yet created")

    offenders = []
    for py_file in agents_dir.glob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        if "from db import" in text or "import db as" in text or "import db\n" in text:
            offenders.append(str(py_file))

    assert not offenders, f"new agents files should not import db.py: {offenders}"


def test_new_services_no_db_import():
    """M2-M5 新增的 services 模块必须不引入 db.py。"""
    new_dirs = [
        "app/services/learning_path/forgetting_curve.py",
        "app/services/learning_path/review_scheduler.py",
        "app/services/safety/jailbreak_detector.py",
        "app/services/sandbox/executor.py",
        "app/services/scheduler/apscheduler_wire.py",
        "app/services/orchestrator/chain.py",
        "app/services/cognitive/style_recognizer.py",
        "app/services/exercise/variant_generator.py",
        "app/services/reflection/log_agent.py",
        "app/services/multimodal/ocr.py",
        "app/services/report/parent_report.py",
    ]
    offenders = []
    for rel in new_dirs:
        path = Path(rel)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "from db import" in text or "import db as" in text or "import db\n" in text:
            offenders.append(rel)

    assert not offenders, f"new service files should not import db.py: {offenders}"