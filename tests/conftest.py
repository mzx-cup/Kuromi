# -*- coding: utf-8 -*-
"""pytest 全局配置 + dual-backend fixtures"""
from __future__ import annotations

import os

import pytest
from pathlib import Path

from tests.fixtures.seed_data import (
    init_legacy_schema,
    init_orm_schema,
    populate_legacy,
    populate_orm,
    SEED_USERS,
)


# Phase 2.3: 收口 — 生产环境 JSON fallback 默认 raise. 但测试套件里大量
# 契约/集成测试模拟 "DB 不可用" 走 JSON fallback 来验证老路径，必须显式
# 打开 dual-write 安全网，否则这些测试会一上来就 RuntimeError. 个别测试
# （如 test_db_local_storage_raises_in_production.py）通过 monkeypatch.delenv
# 显式移除该 flag 来验证 raise 路径。
os.environ.setdefault("DUAL_WRITE_LEGACY", "true")

# P0 Task 2: 启动期严格校验 JWT_SECRET, 缺/弱/占位值会 RuntimeError.
# 这里 setdefault 一个 48 字节随机值, 仅用于本地 pytest 套件.
# 生产/比赛模式必须显式注入 (scripts/start_competition.sh 自动生成).
os.environ.setdefault(
    "JWT_SECRET",
    "test-only-jwt-secret-do-not-use-in-production-aaaaaaaaaaaaaaaaaaaaaaaa",  # 60 字节, 满足 >= 32
)


@pytest.fixture(autouse=True, scope="session")
def _ensure_supervision_tables():
    """slice-B1 + slice-B2: create supervision / drift ORM tables on the
    L1 sync engine so repo queries work under the test DB.

    ``evaluate_all_active_users`` re-imports the ORM repos locally (bypassing
    ``patch.object`` on the module), so the real repository runs against the
    shared ``SessionFactory`` engine — which must have the tables.
    """
    from app.models.base import Base
    from app.models import supervision  # noqa: F401  (register tables)
    from app.models import drift_report  # noqa: F401  (slice-B2 register)
    from app.repositories.orm.knowledge_node import SessionFactory

    with SessionFactory() as s:
        engine = s.get_bind()
        Base.metadata.create_all(
            engine,
            tables=[
                supervision.SupervisionRule.__table__,
                supervision.SupervisionEvent.__table__,
                drift_report.DriftReport.__table__,
            ],
            checkfirst=True,
        )
    yield


def pytest_configure(config):
    """注册自定义 pytest markers"""
    config.addinivalue_line(
        "markers",
        "slow: 标记为慢速测试（需要实际 API 调用或 LLM 请求）"
    )
    config.addinivalue_line(
        "markers",
        "ai: 标记为 AI/LLM 相关测试（需消耗 API 配额）"
    )
    config.addinivalue_line(
        "markers",
        "cv: 标记为 CV 图像/视频相关测试"
    )
    config.addinivalue_line(
        "markers",
        "e2e: 标记为端到端测试（需要运行中的服务）"
    )
    config.addinivalue_line(
        "markers",
        "unit: 标记为单元测试（纯逻辑，无外部依赖）"
    )
    config.addinivalue_line(
        "markers",
        "contract: 契约测试（双套后端对比）"
    )
    config.addinivalue_line(
        "markers",
        "dual_write: 双写一致性测试"
    )
    config.addinivalue_line(
        "markers",
        "perf: 性能测试"
    )


class DualDbEnv:
    def __init__(self, legacy_path: str, orm_path: str):
        self.legacy_path = legacy_path
        self.orm_path = orm_path


class ContractRunner:
    def __init__(self, legacy_client, orm_client):
        self.legacy_client = legacy_client
        self.orm_client = orm_client

    def assert_contract(self, method: str, path: str, **kwargs):
        """Same endpoint, two backends. Responses must match (excluding noise fields)."""
        from tests.fixtures.normalize import normalize

        legacy_resp = self.legacy_client.request(method, path, **kwargs)
        orm_resp = self.orm_client.request(method, path, **kwargs)

        assert legacy_resp.status_code == orm_resp.status_code, (
            f"Status mismatch for {method} {path}: "
            f"legacy={legacy_resp.status_code}, orm={orm_resp.status_code}"
        )

        if legacy_resp.status_code == 200:
            assert normalize(legacy_resp.json()) == normalize(orm_resp.json()), (
                f"Body mismatch for {method} {path}\n"
                f"Legacy: {legacy_resp.json()}\nORM: {orm_resp.json()}"
            )


@pytest.fixture
def dual_db_environment(tmp_path):
    """Create both legacy and ORM databases with identical seed data."""
    legacy_path = str(tmp_path / "legacy.db")
    orm_path = str(tmp_path / "orm.db")

    init_legacy_schema(legacy_path)
    init_orm_schema(orm_path)

    populate_legacy(legacy_path, SEED_USERS)
    populate_orm(orm_path, SEED_USERS)

    return DualDbEnv(legacy_path=legacy_path, orm_path=orm_path)


@pytest.fixture
def contract_runner(dual_db_environment):
    """Provide contract comparison helper."""
    from fastapi.testclient import TestClient
    from main import app

    # For M0, both clients point at the same app. M1+ will route differently.
    legacy_client = TestClient(app)
    orm_client = TestClient(app)

    return ContractRunner(legacy_client=legacy_client, orm_client=orm_client)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset SlowAPI state between every test.

    SlowAPI's in-memory storage accumulates hits per-IP across tests when
    the same TestClient hits the same endpoints. Tests that share the
    testclient IP (``testclient``) would otherwise exhaust rate limits
    and produce spurious 429s. The dedicated rate-limit tests in
    ``tests/security/test_rate_limit.py`` work correctly because they
    rely on per-test state — the reset happens AFTER those tests.
    """
    yield
    try:
        from app.core.rate_limiter import limiter
        limiter.reset()
    except Exception:
        pass
