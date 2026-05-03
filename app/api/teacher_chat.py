# -*- coding: utf-8 -*-
"""
AI 教师对话 API — 画图 + 搜索 + 评分的 SSE 管道

POST /api/v2/teacher/chat  — 文本对话（支持 web_search + draw_svg）
POST /api/v2/teacher/speech — 语音对话（ASR → Pipeline → SSE）
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.teacher.pipeline import get_pipeline
from app.services.teacher.personas import get_persona_manager

logger = logging.getLogger("starlearn.api.teacher_chat")

router = APIRouter(prefix="/teacher", tags=["teacher"])


class TeacherChatRequest(BaseModel):
    """AI 教师对话请求"""
    message: str
    persona: str = "expert_mentor"
    student_id: str = ""
    course_id: str = ""
    scene_context: dict | None = None
    student_profile: dict | None = None


class TeacherSpeechRequest(BaseModel):
    """语音对话请求 — 文本已由前端 ASR 转写"""
    text: str
    persona: str = "expert_mentor"
    student_id: str = ""
    course_id: str = ""


# =============================================================================
# 文本对话端点
# =============================================================================

@router.post("/chat")
async def teacher_chat(req: TeacherChatRequest):
    """
    AI 教师文本对话。

    SSE 事件类型:
      event: text_delta       data: {"content": "..."}
      event: action           data: {"type": "speech", "content": "...", "audioUrl": "..."}
      event: action           data: {"type": "wb_draw_svg", "params": {"svg": "...", ...}}
      event: function_call    data: {"name": "web_search", "arguments": {"query": "..."}}
      event: function_result  data: {"name": "web_search", "result": {...}}
      event: done             data: {"agent": "teacher", "action_count": 5}
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    pipeline = get_pipeline()

    return StreamingResponse(
        _sse_wrap(pipeline.run(
            user_input=req.message,
            persona=req.persona,
            student_id=req.student_id,
            course_id=req.course_id,
            scene_context=req.scene_context,
            student_profile=req.student_profile,
        )),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =============================================================================
# 语音对话端点（文本已由 ASR 转写）
# =============================================================================

@router.post("/speech")
async def teacher_speech(req: TeacherSpeechRequest):
    """
    AI 教师语音对话 — 文本已由前端/ASR 转写。

    等价于 /asr/conversation 的文本输入版本。
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    pipeline = get_pipeline()

    # 获取学生画像
    profile = None
    if req.student_id:
        try:
            from db import get_db
            with get_db() as db:
                cursor = db.execute(
                    "SELECT * FROM student_profiles WHERE user_id = ? LIMIT 1",
                    (req.student_id,),
                )
                row = cursor.fetchone()
                if row:
                    profile = {
                        "cognitive_level": getattr(row, "cognitive_level", ""),
                        "learning_style": getattr(row, "learning_style", ""),
                    }
        except Exception:
            pass

    return StreamingResponse(
        _sse_wrap(pipeline.run(
            user_input=req.text,
            persona=req.persona,
            student_id=req.student_id,
            course_id=req.course_id,
            student_profile=profile,
        )),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =============================================================================
# 辅助
# =============================================================================

async def _sse_wrap(event_stream):
    """将 pipeline 事件流包装为 SSE 格式"""
    async for event in event_stream:
        event_type = event.get("event", "message")
        data = event.get("data", {})
        yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
