# -*- coding: utf-8 -*-
"""
ASR API 端点 — AI 教师的"听觉"

POST /api/v2/asr/transcribe       — 语音→文本（纯转写）
POST /api/v2/asr/conversation     — 语音→文本→AI教师→SSE 流式回复（端到端）
GET  /api/v2/asr/providers         — 列出 ASR Provider

对应 OpenMAIC app/api/transcription/route.ts
增强：/conversation 端点实现"听+说"全链路（OpenMAIC 中 ASR 和 Chat 是分离的两次调用）
"""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.services.asr.registry import get_asr_provider, list_providers
from app.services.teacher.personas import get_persona_manager

logger = logging.getLogger("starlearn.api.asr")

router = APIRouter(prefix="/asr", tags=["asr"])


# =============================================================================
# 纯转写端点（已有）
# =============================================================================

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    provider_id: str = Form(default="baidu-asr"),
):
    """上传音频文件并转写为文字"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No audio file provided")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio data is empty")

    audio_format = _detect_format(file.filename)

    try:
        provider = get_asr_provider(provider_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = await provider.transcribe(audio_bytes, audio_format)
        logger.info(
            "ASR transcribed: provider=%s, text_len=%d, confidence=%.2f",
            provider_id, len(result.text), result.confidence,
        )
        return {
            "success": True,
            "text": result.text,
            "language": result.language,
            "confidence": result.confidence,
        }
    except Exception as e:
        logger.error("ASR transcription failed [provider=%s]: %s", provider_id, e)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 端到端对话端点 — 星识增强（OpenMAIC 无此一体化能力）
# =============================================================================

@router.post("/conversation")
async def speech_to_conversation(
    file: UploadFile = File(...),
    asr_provider: str = Form(default="baidu-asr"),
    student_id: str = Form(default=""),
    persona: str = Form(default="expert_mentor"),
    course_id: str = Form(default=""),
    scene_id: str = Form(default=""),
):
    """
    语音 → 文本 → AI 教师 → SSE 流式回复（端到端）。

    一步完成：
    1. ASR 转写语音为文本
    2. 将文本作为学生提问，送入 AI 教师对话流
    3. 返回 SSE 流（Action JSON 数组），包含教师语音 + 视觉动作

    前端只需调用此端点一次，即可获得完整的教师回复流。
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No audio file provided")

    # ---- Step 1: ASR 转写 ----
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio data is empty")

    audio_format = _detect_format(file.filename)

    try:
        asr = get_asr_provider(asr_provider)
        result = await asr.transcribe(audio_bytes, audio_format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("ASR failed in conversation: %s", e)
        raise HTTPException(status_code=500, detail=f"语音识别失败: {e}")

    user_text = result.text.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="语音识别结果为空，请重新说话")

    logger.info(
        "Speech→Conversation: student=%s, text=%s, persona=%s",
        student_id, user_text[:80], persona,
    )

    # ---- Step 2: AI 教师对话流 ----
    return StreamingResponse(
        _teacher_conversation_stream(
            user_text=user_text,
            student_id=student_id,
            persona=persona,
            course_id=course_id,
            scene_id=scene_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _teacher_conversation_stream(
    user_text: str,
    student_id: str = "",
    persona: str = "expert_mentor",
    course_id: str = "",
    scene_id: str = "",
):
    """
    生成 AI 教师对话 SSE 流。

    事件类型:
      event: asr_result   data: {"text": "转写文本", "confidence": 0.95}
      event: action       data: {"type": "speech", "content": "...", "audioUrl": "..."}
      event: action       data: {"type": "spotlight", "params": {...}}
      event: text_delta   data: {"content": "..."}
      event: done         data: {"agent": "teacher"}
    """
    # 1. 发送 ASR 结果
    yield _sse("asr_result", {"text": user_text, "confidence": 1.0})

    # 2. 组装 System Prompt
    mgr = get_persona_manager()
    system_prompt = mgr.build_system_prompt(
        persona_id=persona,
        student_profile=_get_student_profile(student_id),
        scene_context={"scene_type": "slide"} if scene_id else None,
    )

    # 3. 构建用户消息
    user_message = f"学生提问：{user_text}\n请根据你的教学风格，用碎片化交织的方式回答。边说边画，边说边指。"

    # 4. 调用 LLM 流式生成
    try:
        from llm_stream import call_llm_async_stream

        # 流式生成（如果可用）
        full_response = ""
        async for chunk in call_llm_async_stream(system_prompt, user_message, temperature=0.7):
            full_response += chunk
            yield _sse("text_delta", {"content": chunk})

        # 5. 解析 JSON Action 数组
        # LLM 输出的是 JSON 数组，需要提取和验证
        actions = _extract_actions(full_response)
        if actions:
            for action in actions:
                # 为 speech action 预生成 TTS
                if action.get("type") == "speech":
                    action = await _pre_generate_tts(action)
                yield _sse("action", action)

    except Exception as e:
        logger.error("Teacher conversation stream error: %s", e)
        yield _sse("error", {"message": str(e)})

    yield _sse("done", {"agent": "teacher", "persona": persona})


# =============================================================================
# 元数据端点
# =============================================================================

@router.get("/providers")
async def list_asr_providers():
    """列出所有 ASR Provider"""
    return {"providers": list_providers()}


# =============================================================================
# 内部辅助
# =============================================================================

def _detect_format(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if filename else ""
    return ext if ext in ("wav", "mp3", "ogg", "m4a", "webm") else "webm"


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _extract_actions(raw_response: str) -> list[dict] | None:
    """从 LLM 原始输出中提取 JSON Action 数组"""
    import re
    text = raw_response.strip()

    # 移除可能的代码块标记
    if text.startswith("```"):
        text = re.sub(r"^```\w*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    # 尝试找到 JSON 数组
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        return None

    try:
        actions = json.loads(match.group(0))
        if isinstance(actions, list):
            return actions
    except json.JSONDecodeError:
        pass
    return None


async def _pre_generate_tts(action: dict) -> dict:
    """为 speech action 预生成 TTS 音频"""
    text = action.get("content") or action.get("params", {}).get("content", "")
    if not text or len(text) < 2:
        return action

    try:
        from app.services.tts.registry import get_tts_provider
        from app.services.tts.types import TTSConfig
        import base64

        provider = get_tts_provider("minimax-tts")
        config = TTSConfig(provider_id="minimax-tts", voice="female-shaonv", speed=1.0)
        result = await provider.generate(text, config)

        action["audioUrl"] = (
            "data:audio/" + result.format + ";base64,"
            + base64.b64encode(result.audio).decode("ascii")
        )
        action["durationMs"] = result.duration_ms
    except Exception as e:
        logger.warning("TTS pre-generation in conversation stream failed: %s", e)

    return action


def _get_student_profile(student_id: str) -> dict | None:
    """从数据库获取学生画像"""
    if not student_id:
        return None

    try:
        from db import get_db
        with get_db() as db:
            cursor = db.execute(
                "SELECT * FROM student_profiles WHERE user_id = ? OR user_id = %s LIMIT 1",
                (student_id, student_id),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "nickname": getattr(row, "nickname", ""),
                    "cognitive_level": getattr(row, "cognitive_level", ""),
                    "learning_style": getattr(row, "learning_style", ""),
                    "learning_goals": getattr(row, "learning_goals", ""),
                }
    except Exception as e:
        logger.debug("Failed to fetch student profile: %s", e)

    return None
