# -*- coding: utf-8 -*-
"""P0 Task 12: 演示主链 HTTP 端点 (P1 阶段 P1 Task 14 接入真实 engine).

设计目标:
  让前端能"点一个按钮 → 看 8 步 trace 实际跑" 的可视化演示.
  提供 2 个端点:
    - POST /api/demo/run-live-path : 跑一次完整主链, 返回 LivePathResult.to_dict()
    - GET  /api/demo/health         : 演示服务自检 (端点是否在线, 内部组件 OK)

鉴权策略:
  - 教师/管理员可触发 (走 require_teacher 守卫)
  - 学生也可触发 (走 require_user_or_teacher, 以 user_id == student_id 匹配)
  - 演示数据是合成的 (DemoRepository), 无 PII 风险, 但要求登录保留追溯

降级:
  任何一步失败 → 200 (主链不断) + step.fallback=True
  整链失败 → 500 + 详细 trace_id 便于现场回放
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.services.demo_runner import LivePathResult, run_live_demo_path

logger = logging.getLogger("starlearn.api.demo_path")

router = APIRouter(prefix="/api/demo", tags=["demo"])


class RunLivePathRequest(BaseModel):
    """POST /api/demo/run-live-path 请求体.

    字段:
        user_id: 演示用户 ID (默认 demo_student_1, 比赛现场也是这个账号).
        scenario: 场景名 (预留, 给 P2 阶段多场景演示用).
    """

    user_id: str = "demo_student_1"
    scenario: str = "default"


@router.post("/run-live-path")
async def post_run_live_path(
    body: RunLivePathRequest,
    request: Request,
) -> dict[str, Any]:
    """跑一次完整演示主链, 返回 8 步 trace.

    行为契约:
      - 始终 200 (除非 main.py 框架级错误)
      - body.trace_id 必填, 形如 ``lp_<12hex>``
      - body.steps 必填, 每步含 {name, ok, ts_ms, fallback, trace_id, error, data}
      - body.fallback_used 表示是否有任一步降级
      - body.elapsed_ms 表示全链总耗时
    """
    # P1 Task 21: 鉴权 (学生: 仅自己; 教师/管理员: 任意)
    from app.api.auth import require_user_or_teacher
    require_user_or_teacher(body.user_id, request)

    result: LivePathResult = await run_live_demo_path(
        user_id=body.user_id, scenario=body.scenario
    )
    return result.to_dict()


@router.get("/run-live-path")
async def get_run_live_path(
    request: Request,
    user_id: str = Query("demo_student_1", description="演示用户 ID"),
    scenario: str = Query("default", description="场景名 (P2 预留)"),
) -> dict[str, Any]:
    """GET 版本 (便于浏览器手测, 不依赖 POST/JSON)."""
    from app.api.auth import require_user_or_teacher
    require_user_or_teacher(user_id, request)

    result: LivePathResult = await run_live_demo_path(
        user_id=user_id, scenario=scenario
    )
    return result.to_dict()


@router.get("/health")
async def demo_health() -> dict[str, Any]:
    """演示服务自检 — 端点是否在线 + 内部模块能否加载."""
    from app.services.repository import DemoRepository
    from app.services.tutor_engine.engine import TutorDecisionEngine

    components: dict[str, str] = {}
    try:
        DemoRepository()
        components["demo_repository"] = "ok"
    except Exception as exc:  # noqa: BLE001
        components["demo_repository"] = f"error: {exc}"

    try:
        TutorDecisionEngine()
        components["tutor_engine"] = "ok"
    except Exception as exc:  # noqa: BLE001
        components["tutor_engine"] = f"error: {exc}"

    overall = "ok" if all(v == "ok" for v in components.values()) else "degraded"
    return {"status": overall, "components": components}
