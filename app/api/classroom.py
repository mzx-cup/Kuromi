from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.core.database import get_sessionmaker
from app.core.sse import sse_done, sse_event
from app.models.classroom import ClassroomSession

logger = logging.getLogger("starlearn.classroom")

router = APIRouter(prefix="/api/classroom", tags=["classroom"])


class StreamRequest(BaseModel):
    message: str = ""
    store_state: dict | None = None
    config: dict | None = None
    user_profile: dict | None = None


async def classroom_stream(req: StreamRequest):
    """
    Mock SSE stream endpoint (Phase 1.3).
    Pushes fake token deltas and Action events to validate
    the frontend fetch + ReadableStream + SSEParser pipeline.
    Route registered in main.py as POST /api/v2/classroom/stream.
    """
    logger.info("Mock classroom stream for: %s", req.message[:80] if req.message else "(empty)")

    async def event_generator():
        intro = "同学们好，今天我们来学习一个有趣的知识点。"
        for char in intro:
            yield sse_event("text_delta", {"content": char})
            await asyncio.sleep(0.04)

        yield sse_event("action", {
            "type": "action",
            "name": "spotlight",
            "params": {"elementId": "title-bar"},
        })

        await asyncio.sleep(0.6)

        body = "首先，让我们看看核心概念的定义。这个概念非常重要，大家注意听讲。"
        for char in body:
            yield sse_event("text_delta", {"content": char})
            await asyncio.sleep(0.04)

        yield sse_event("action", {
            "type": "action",
            "name": "wb_draw_text",
            "params": {"text": "核心概念", "x": 100, "y": 100},
        })

        await asyncio.sleep(0.5)

        closing = "理解了基本概念之后，我们来做一个小测验吧。"
        for char in closing:
            yield sse_event("text_delta", {"content": char})
            await asyncio.sleep(0.04)

        yield sse_event("action", {
            "type": "action",
            "name": "quiz_show",
            "params": {
                "quizData": {
                    "title": "概念检测",
                    "questions": [{
                        "question": "以下哪项描述最准确？",
                        "options": ["选项A", "选项B", "选项C", "选项D"],
                        "correct_answer": 1,
                    }],
                },
            },
        })

        yield sse_done(agent_name="teacher", full_text=intro + body + closing)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions/{session_id}")
async def get_classroom_session(session_id: str, include_demo: bool = True):
    """Fetch a ClassroomSession by id. Demo sessions (is_demo=TRUE) are loaded
    if include_demo is True (default). Returns a JSON envelope matching the
    standard {code, data} shape used elsewhere."""
    sm = get_sessionmaker()
    async with sm() as session:
        stmt = select(ClassroomSession).where(ClassroomSession.id == session_id)
        if not include_demo:
            stmt = stmt.where(ClassroomSession.is_demo.is_(False))
        row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Classroom session not found")
    return {
        "code": 200,
        "data": {
            "id": row.id,
            "course_id": row.course_id,
            "title": (row.course_data or {}).get("title") if isinstance(row.course_data, dict) else "",
            "teacher_persona": row.teacher_persona,
            "status": row.status,
            "slides": row.slides,
            "is_demo": bool(getattr(row, "is_demo", False)),
            "demo_version": getattr(row, "demo_version", "") or "",
            "created_at": row.created_at.isoformat() if row.created_at else None,
        },
    }

