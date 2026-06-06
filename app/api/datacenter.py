"""
Datacenter API — 数据仪表盘 API

GET  /api/datacenter/stats   — 统计数据
GET  /api/datacenter/trends  — 趋势数据
GET  /api/datacenter/events  — SSE 实时事件流
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger("starlearn.datacenter")

router = APIRouter(prefix="/api/datacenter")


@router.get("/stats")
def get_stats(level: str = Query("school")):
    """获取数据仪表盘统计数据。

    Args:
        level: 数据层级 (school / class / student)
    """
    now = datetime.now().isoformat()
    return {
        "stats": {
            "totalStudents": 0,
            "activeStudents": 0,
            "totalClasses": 0,
            "totalCourses": 0,
            "avgEngagement": 0,
            "avgScore": 0,
            "completionRate": 0,
            "updatedAt": now,
        }
    }


@router.get("/trends")
def get_trends(level: str = Query("school")):
    """获取趋势数据。

    Args:
        level: 数据层级 (school / class / student)
    """
    return {
        "trends": [],
        "points": [],
        "updatedAt": datetime.now().isoformat(),
    }


@router.get("/events")
async def datacenter_events(request: Request, level: str = Query("school")):
    """SSE 端点 — 推送数据仪表盘的实时事件。

    每 30 秒发送一次心跳，保持连接活跃。
    """
    async def event_generator():
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                # Send heartbeat with current timestamp
                event_data = {
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat(),
                    "level": level,
                }
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

                await asyncio.sleep(30)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
