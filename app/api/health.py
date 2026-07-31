# -*- coding: utf-8 -*-
"""``/api/health`` — 比赛演示标准化健康检查端点.

设计原则:
- 子系统独立评估, 任一降级不影响其它子项报告.
- 总状态聚合规则: 任一 ``down`` -> ``down``; 任一 ``degraded`` -> ``degraded``; 否则 ``ok``.
- 各子项可被标记 ``skipped`` (例: Qdrant 在非向量检索场景下不强制启用).
- 子项检查必须**短超时** (≤ 2s), 避免健康检查本身拖垮启动时间.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger("starlearn.api.health")

router = APIRouter()


def _safe_db_check() -> dict[str, Any]:
    """DB 子项: 极简 ping, 不引入对 ORM 的硬依赖.

    P0 阶段只检查环境变量 + 引擎对象能否被 import. 真实连接检查由各业务路由的
    第一次 SQL 触发; 失败会写入 trace, 不会让 /api/health 阻塞.
    """
    try:
        # 软导入: 即便 SQLAlchemy 未配置也允许 /api/health 报告.
        from app.core.database import get_sessionmaker  # noqa: WPS433

        _ = get_sessionmaker
        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        # 缺依赖不是 DB 不可用, 标记 degraded 而不是 down.
        return {"status": "degraded", "error": f"db import: {exc}"}


async def _check_llm() -> dict[str, Any]:
    """LLM 子项: 检查 provider 是否存在, 不发真实请求."""
    try:
        # 仅验证模块可导入, 不发网络请求, 避免健康检查拖慢启动.
        from app.services.llm import retry_strategy  # noqa: WPS433,F401

        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "error": str(exc)}


async def _check_kb() -> dict[str, Any]:
    """KB 子项: 检查 retriever 模块可导入."""
    try:
        from app.services.kb import citation_retriever  # noqa: WPS433,F401

        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "error": str(exc)}


async def _check_qdrant() -> dict[str, Any]:
    """Qdrant 子项: 向量库在比赛模式下不强制要求, 默认 skipped.

    若 ``STARLEARN_REQUIRE_QDRANT=1``, 则尝试 import client 并报告 ok/degraded.
    """
    if os.environ.get("STARLEARN_REQUIRE_QDRANT") != "1":
        return {"status": "skipped", "reason": "Qdrant not required in competition mode"}

    try:
        from app.services.kb import qdrant_client  # noqa: WPS433,F401

        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "error": str(exc)}


@router.get("/api/health")
async def health() -> dict[str, Any]:
    """聚合 4 个子系统状态, 返回标准化 JSON."""
    llm, kb, qd = await asyncio.gather(
        _check_llm(), _check_kb(), _check_qdrant()
    )
    db = _safe_db_check()

    components = {"llm": llm, "kb": kb, "db": db, "qdrant": qd}
    statuses = {c["status"] for c in components.values()}

    if "down" in statuses:
        overall = "down"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "ok"

    return {
        "status": overall,
        "components": components,
    }
