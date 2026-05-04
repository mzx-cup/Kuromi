"""
MiniMax 媒体生成封装
支持: image-01 (文生图), speech-02 (TTS), video-01 (文生视频)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger("starlearn.media")

_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=15.0, read=120.0, write=30.0, pool=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


# ----------------------------------------------------------------
# Image Generation (image-01)
# ----------------------------------------------------------------

# Image endpoint: {minimax_api_url}/image_generation
IMAGE_GENERATION_URL = "{base}/image_generation"


async def generate_image(
    prompt: str,
    aspect_ratio: str = "16:9",
    model: str = "",
    api_key: str = "",
) -> str:
    """
    调用 MiniMax image-01 生成图片
    返回: 图片URL
    """
    client = await get_client()
    key = api_key or settings.minimax_api_key
    model_name = model or settings.minimax_image_model

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json; charset=utf-8",
    }

    payload = {
        "model": model_name,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "response_format": "url",
        "n": 1,
        "prompt_optimizer": False,
    }

    image_url = IMAGE_GENERATION_URL.format(base=settings.minimax_api_url)
    logger.info(f"Generating image: model={model_name}, prompt={prompt[:60]}...")
    response = await client.post(image_url, headers=headers, json=payload)

    if response.status_code != 200:
        raise RuntimeError(
            f"MiniMax Image API error HTTP {response.status_code}: {response.text[:200]}"
        )

    data = response.json()

    # Check MiniMax error response
    base_resp = data.get("base_resp", {})
    if base_resp.get("status_code", 0) != 0:
        raise RuntimeError(
            f"MiniMax Image API error {base_resp.get('status_code')}: {base_resp.get('status_msg', 'unknown')}"
        )

    image_urls = data.get("data", {}).get("image_urls", [])
    if not image_urls:
        raise RuntimeError(f"MiniMax Image: no image URLs returned: {json.dumps(data)[:200]}")

    logger.info(f"Image generated successfully: {image_urls[0][:80]}...")
    return image_urls[0]


# ----------------------------------------------------------------
# TTS Generation (speech-02 / t2a_v2)
# ----------------------------------------------------------------

# TTS endpoint: {minimax_api_url}/t2a_v2?GroupId={group_id}

# 语音角色配置
TTS_VOICE_CONFIGS: list[dict] = [
    {"id": "female-shaonv", "name": "青春少女", "desc": "活泼明亮的少女声音"},
    {"id": "female-yujie", "name": "温柔御姐", "desc": "温柔成熟的女性声音"},
    {"id": "female-danyun", "name": "知性女声", "desc": "沉稳知性的女声"},
    {"id": "male-qingshu", "name": "青涩少年", "desc": "年轻活力的男声"},
    {"id": "male-shaoshuai", "name": "磁性男声", "desc": "低沉磁性的男声"},
]


async def generate_tts(
    text: str,
    voice_id: str = "female-shaonv",
    speed: float = 1.0,
    model: str = "",
    api_key: str = "",
    group_id: str = "",
) -> bytes:
    """
    调用 MiniMax speech-02 TTS 生成语音
    返回: 原始音频字节 (MP3格式)
    """
    client = await get_client()
    key = api_key or settings.minimax_api_key
    gid = group_id or settings.minimax_group_id
    model_name = model or settings.minimax_tts_model

    url = f"{settings.minimax_api_url}/t2a_v2?GroupId={gid}"

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_name,
        "text": text.strip(),
        "stream": False,
        "voice_setting": {
            "voice_id": voice_id,
            "speed": speed,
            "vol": 1.0,
            "pitch": 0,
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        },
    }

    logger.info(f"Generating TTS: model={model_name}, voice={voice_id}, text_len={len(text)}")
    response = await client.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise RuntimeError(
            f"MiniMax TTS API error HTTP {response.status_code}: {response.text[:200]}"
        )

    data = response.json()

    # Check MiniMax error response
    base_resp = data.get("base_resp", {})
    if base_resp.get("status_code", 0) != 0:
        raise RuntimeError(
            f"MiniMax TTS API error {base_resp.get('status_code')}: {base_resp.get('status_msg', 'unknown')}"
        )

    audio_data = data.get("data", {}).get("audio")
    if not audio_data:
        raise RuntimeError(f"MiniMax TTS: no audio data returned: {json.dumps(data)[:200]}")

    # audio_data is hex-encoded string
    audio_bytes = bytes.fromhex(audio_data)
    logger.info(f"TTS generated: {len(audio_bytes)} bytes")
    return audio_bytes


# ----------------------------------------------------------------
# Video Generation (可灵Kling)
# ----------------------------------------------------------------


async def generate_video(
    prompt: str,
    duration: int = 5,
    resolution: str = "720p",
) -> str:
    """
    调用可灵Kling API生成视频
    返回: 视频下载URL
    """
    if not settings.kling_access_key or not settings.kling_secret_key:
        raise RuntimeError("可灵API密钥未配置，请检查config/.env中的KLING_ACCESS_KEY和KLING_SECRET_KEY")

    from kling_api import generate_video_text
    return await generate_video_text(
        prompt=prompt,
        duration=duration,
        resolution=resolution,
        poll_interval=5,
        max_poll_time=600,
    )
