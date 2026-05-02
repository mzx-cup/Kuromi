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
# Video Generation (video-01) - Job-based polling
# ----------------------------------------------------------------

# Video endpoints: {minimax_api_url}/video_generation, /query/video_generation, /files/retrieve
VIDEO_SUBMIT_URL = "{base}/video_generation"
VIDEO_QUERY_URL = "{base}/query/video_generation"
VIDEO_RETRIEVE_URL = "{base}/files/retrieve"


async def generate_video(
    prompt: str,
    duration: int = 6,
    resolution: str = "720P",
    model: str = "",
    api_key: str = "",
    poll_interval: int = 5,
    max_poll_time: int = 300,
) -> str:
    """
    调用 MiniMax video-01 生成视频（基于任务轮询模式）
    返回: 视频下载URL
    """
    client = await get_client()
    key = api_key or settings.minimax_api_key
    model_name = model or settings.minimax_video_model
    api_base = settings.minimax_api_url

    # Step 1: Submit task
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json; charset=utf-8",
    }

    submit_payload = {
        "model": model_name,
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
    }

    submit_url = VIDEO_SUBMIT_URL.format(base=api_base)
    logger.info(f"Submitting video generation: model={model_name}, prompt={prompt[:60]}...")
    submit_resp = await client.post(submit_url, headers=headers, json=submit_payload)

    if submit_resp.status_code != 200:
        raise RuntimeError(
            f"MiniMax Video submit error HTTP {submit_resp.status_code}: {submit_resp.text[:200]}"
        )

    submit_data = submit_resp.json()
    base_resp = submit_data.get("base_resp", {})
    if base_resp.get("status_code", 0) != 0:
        raise RuntimeError(
            f"MiniMax Video submit error {base_resp.get('status_code')}: {base_resp.get('status_msg')}"
        )

    task_id = submit_data.get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id in MiniMax video response: {json.dumps(submit_data)[:200]}")

    logger.info(f"Video task submitted: task_id={task_id}")

    # Step 2: Poll for completion
    start_time = time.time()
    while time.time() - start_time < max_poll_time:
        await asyncio.sleep(poll_interval)

        query_url = VIDEO_QUERY_URL.format(base=api_base)
        query_resp = await client.get(
            f"{query_url}?task_id={task_id}",
            headers=headers,
        )

        if query_resp.status_code != 200:
            logger.warning(f"Video query error HTTP {query_resp.status_code}, retrying...")
            continue

        query_data = query_resp.json()
        status = query_data.get("status", "")

        logger.info(f"Video task {task_id} status: {status}")

        if status == "Success":
            file_id = query_data.get("file_id")
            if not file_id:
                raise RuntimeError(f"No file_id in MiniMax video query: {json.dumps(query_data)[:200]}")

            # Step 3: Retrieve download URL
            retrieve_url = VIDEO_RETRIEVE_URL.format(base=api_base)
            retrieve_resp = await client.get(
                f"{retrieve_url}?file_id={file_id}",
                headers=headers,
            )

            if retrieve_resp.status_code != 200:
                raise RuntimeError(
                    f"MiniMax file retrieve error HTTP {retrieve_resp.status_code}"
                )

            retrieve_data = retrieve_resp.json()
            download_url = retrieve_data.get("file", {}).get("download_url", "")
            if not download_url:
                raise RuntimeError(f"No download_url in MiniMax file retrieve")

            logger.info(f"Video generated successfully: {download_url[:80]}...")
            return download_url

        elif status == "Fail":
            raise RuntimeError(f"MiniMax video generation failed: {json.dumps(query_data)[:200]}")

        # "Preparing", "Queueing", "Processing" → continue polling

    raise RuntimeError(f"MiniMax video generation timed out after {max_poll_time}s")
