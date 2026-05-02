# -*- coding: utf-8 -*-
"""
TTS API 端点

POST /api/v2/tts/generate       — 非流式 TTS 生成
POST /api/v2/tts/stream           — 流式 TTS（SSE: 音频块 + 字级时间戳）
GET  /api/v2/tts/voices/{id}     — 获取音色列表
GET  /api/v2/tts/providers        — 列出 Provider

对应 OpenMAIC app/api/generate/tts/route.ts
增强：流式端点 + 字级时间戳（星识超越 OpenMAIC 的能力）
"""

from __future__ import annotations

import base64
import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.tts.registry import get_tts_provider, list_providers
from app.services.tts.types import TTSConfig, TTSStreamChunk

logger = logging.getLogger("starlearn.api.tts")

router = APIRouter(prefix="/tts", tags=["tts"])


class TTSRequest(BaseModel):
    text: str
    provider_id: str = "minimax-tts"
    voice: str = "female-shaonv"
    speed: float = 1.0
    audio_format: str = "mp3"
    model_id: str | None = None
    tts_api_key: str | None = None
    tts_base_url: str | None = None


class TTSResponse(BaseModel):
    audio_base64: str
    format: str
    duration_ms: int
    word_timestamps: list[dict] = []
    sentences: list[dict] = []


# =============================================================================
# 非流式端点
# =============================================================================

@router.post("/generate", response_model=TTSResponse)
async def generate_tts(req: TTSRequest):
    """生成 TTS 音频。返回 base64 编码的完整音频数据。"""
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    config = _build_config(req)

    try:
        provider = get_tts_provider(req.provider_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = await provider.generate(req.text, config)
    except Exception as e:
        logger.error("TTS generation failed [provider=%s]: %s", req.provider_id, e)
        raise HTTPException(status_code=500, detail=str(e))

    audio_b64 = base64.b64encode(result.audio).decode("ascii")
    logger.info(
        "TTS generated: provider=%s, text_len=%d, audio_bytes=%d, duration_ms=%d",
        req.provider_id, len(req.text), len(result.audio), result.duration_ms,
    )
    return TTSResponse(
        audio_base64=audio_b64,
        format=result.format,
        duration_ms=result.duration_ms,
        word_timestamps=result.word_timestamps,
        sentences=result.sentences,
    )


# =============================================================================
# 流式端点 — 星识增强（OpenMAIC 无此能力）
# =============================================================================

@router.post("/stream")
async def stream_tts(req: TTSRequest):
    """
    流式 TTS 合成 + 字级时间戳。

    返回 SSE 事件流:
      event: audio      data: {"hex": "<hex编码的音频增量>"}
      event: word       data: {"word": "你", "start_ms": 120, "end_ms": 340}
      event: done       data: {"format": "mp3"}

    前端可以：
    1. 边接收边播放音频（MediaSource Extensions 或分段 Audio）
    2. 根据 word 事件同步触发字级高亮动画
    """
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    config = _build_config(req)

    try:
        provider = get_tts_provider(req.provider_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    async def event_generator():
        try:
            async for chunk in provider.generate_stream(req.text, config):
                if chunk.audio:
                    yield _sse("audio", {
                        "hex": chunk.audio.hex(),
                    })
                if chunk.word:
                    yield _sse("word", {
                        "word": chunk.word.word,
                        "start_ms": chunk.word.start_ms,
                        "end_ms": chunk.word.end_ms,
                        "sentence_index": chunk.sentence_index,
                    })
                if chunk.is_final:
                    yield _sse("done", {"format": req.audio_format})
        except Exception as e:
            logger.error("TTS stream failed: %s", e)
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =============================================================================
# 元数据端点
# =============================================================================

@router.get("/voices/{provider_id}")
async def list_voices(provider_id: str):
    """获取指定 Provider 的音色列表"""
    try:
        provider = get_tts_provider(provider_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    voices = await provider.get_voices()
    return {"provider_id": provider_id, "voices": voices}


@router.get("/providers")
async def list_tts_providers():
    """列出所有已注册的 TTS Provider"""
    return {"providers": list_providers()}


# =============================================================================
# helpers
# =============================================================================

def _build_config(req: TTSRequest) -> TTSConfig:
    return TTSConfig(
        provider_id=req.provider_id,
        model_id=req.model_id,
        voice=req.voice,
        speed=req.speed,
        audio_format=req.audio_format,
        api_key=req.tts_api_key,
        base_url=req.tts_base_url,
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
