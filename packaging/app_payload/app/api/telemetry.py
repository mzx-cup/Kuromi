# -*- coding: utf-8 -*-
"""前端遥测接收 - 批量埋点写入内存缓冲区(供 portrait_aggregator 消费).

路由风格: 与 agent_orchestration 一致 —— 内部路径写全路径(/api/telemetry),
main.py 用 ``app.include_router(telemetry_router)`` 无 prefix 挂载.

消费者(后续 Task 的 portrait_aggregator v2 等)通过 ``get_telemetry(student_id)`` 拉取.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["telemetry"])

# student_id → list[telemetry events] (供 portrait_aggregator 等消费者读取)
_TELEMETRY_BUFFER: dict[str, list[dict]] = {}


class TelemetryBatch(BaseModel):
    student_id: str
    batch: list[dict]


@router.post("/api/telemetry")
async def post_telemetry(payload: TelemetryBatch):
    """接收前端批量埋点,合并到内存缓冲.

    返回 {accepted, buffer_size} 供前端确认已落盘.
    """
    buf = _TELEMETRY_BUFFER.setdefault(payload.student_id, [])
    buf.extend(payload.batch)
    return {"accepted": len(payload.batch), "buffer_size": len(buf)}


def get_telemetry(student_id: str) -> list[dict]:
    """消费者读取入口(由 portrait_aggregator 等调用)."""
    return _TELEMETRY_BUFFER.get(student_id, [])


def clear_telemetry(student_id: str) -> None:
    """测试/管理用清理函数."""
    _TELEMETRY_BUFFER.pop(student_id, None)
