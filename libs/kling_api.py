"""
可灵Kling AI视频生成API封装
支持文字生成视频和图片生成视频
文档: https://www.klingai.com/docs/api/video/
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import base64
import json
import logging
import time
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger("starlearn.kling")

_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=15.0, read=180.0, write=30.0, pool=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


def _sign_request(access_key: str, secret_key: str, timestamp: int) -> str:
    """生成请求签名"""
    sign_str = f"{access_key}{timestamp}"
    signature = hmac.new(
        secret_key.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode("utf-8")


def _get_headers(access_key: str, secret_key: str) -> dict:
    """生成认证请求头"""
    timestamp = int(time.time() * 1000)
    signature = _sign_request(access_key, secret_key, timestamp)
    return {
        "X-Access-Key": access_key,
        "X-Signature": signature,
        "X-Timestamp": str(timestamp),
        "Content-Type": "application/json; charset=utf-8",
    }


async def generate_video_text(
    prompt: str,
    duration: int = 5,
    aspect_ratio: str = "16:9",
    prompt_strength: float = 1.0,
    resolution: str = "720p",
    cfg_scale: float = 7.5,
    poll_interval: int = 5,
    max_poll_time: int = 600,
) -> str:
    """
    可灵文字生成视频 API
    返回: 视频下载URL

    Args:
        prompt: 视频描述文本
        duration: 视频时长(秒)，支持5/10秒
        aspect_ratio: 画面比例，如 "16:9", "9:16", "1:1"
        prompt_strength: 提示词强度，0.0-1.0
        resolution: 分辨率，"720p" / "1080p"
        cfg_scale: 引导强度
        poll_interval: 轮询间隔(秒)
        max_poll_time: 最大轮询时间(秒)
    """
    client = await get_client()
    access_key = settings.kling_access_key
    secret_key = settings.kling_secret_key

    if not access_key or not secret_key:
        raise RuntimeError("可灵API密钥未配置，请检查config/.env中的KLING_ACCESS_KEY和KLING_SECRET_KEY")

    submit_url = f"{settings.kling_api_url}/videos/text2video"
    headers = _get_headers(access_key, secret_key)

    submit_payload = {
        "model": "kling-v1",
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "prompt_strength": prompt_strength,
        "resolution": resolution,
        "cfg_scale": cfg_scale,
    }

    logger.info(f"[Kling] Submitting text2video: prompt={prompt[:60]}...")
    submit_resp = await client.post(submit_url, headers=headers, json=submit_payload)

    if submit_resp.status_code != 200:
        raise RuntimeError(f"Kling API error HTTP {submit_resp.status_code}: {submit_resp.text[:300]}")

    submit_data = submit_resp.json()
    if submit_data.get("code") != 0:
        raise RuntimeError(f"Kling API error: {submit_data.get('message', submit_data)}")

    task_id = submit_data.get("data", {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id in Kling response: {json.dumps(submit_data)[:200]}")

    logger.info(f"[Kling] Video task submitted: task_id={task_id}")

    # 轮询任务状态
    start_time = time.time()
    query_url = f"{settings.kling_api_url}/videos/text2video/{task_id}"

    while time.time() - start_time < max_poll_time:
        await asyncio.sleep(poll_interval)

        poll_headers = _get_headers(access_key, secret_key)
        poll_resp = await client.get(query_url, headers=poll_headers)

        if poll_resp.status_code != 200:
            logger.warning(f"[Kling] Query error HTTP {poll_resp.status_code}, retrying...")
            continue

        poll_data = poll_resp.json()
        status = poll_data.get("data", {}).get("status", "")

        logger.info(f"[Kling] Task {task_id} status: {status}")

        if status == "completed":
            video_data = poll_data.get("data", {}).get("video", {})
            download_url = video_data.get("url") or video_data.get("download_url")
            if not download_url:
                raise RuntimeError(f"No download_url in Kling response: {json.dumps(poll_data)[:300]}")
            logger.info(f"[Kling] Video generated successfully: {download_url[:80]}...")
            return download_url

        elif status == "failed":
            raise RuntimeError(f"Kling video generation failed: {poll_data.get('message', poll_data)}")

        # "pending" / "processing" -> continue polling

    raise RuntimeError(f"Kling video generation timed out after {max_poll_time}s (task_id={task_id})")


async def generate_video_image(
    image_url: str,
    prompt: str,
    duration: int = 5,
    aspect_ratio: str = "16:9",
    prompt_strength: float = 1.0,
    resolution: str = "720p",
    cfg_scale: float = 7.5,
    poll_interval: int = 5,
    max_poll_time: int = 600,
) -> str:
    """
    可灵图片生成视频 API
    返回: 视频下载URL

    Args:
        image_url: 输入图片的URL
        prompt: 视频描述文本
        duration: 视频时长(秒)，支持5/10秒
        aspect_ratio: 画面比例
        prompt_strength: 提示词强度
        resolution: 分辨率
        cfg_scale: 引导强度
        poll_interval: 轮询间隔(秒)
        max_poll_time: 最大轮询时间(秒)
    """
    client = await get_client()
    access_key = settings.kling_access_key
    secret_key = settings.kling_secret_key

    if not access_key or not secret_key:
        raise RuntimeError("可灵API密钥未配置，请检查config/.env中的KLING_ACCESS_KEY和KLING_SECRET_KEY")

    submit_url = f"{settings.kling_api_url}/videos/image2video"
    headers = _get_headers(access_key, secret_key)

    submit_payload = {
        "model": "kling-v1",
        "image_url": image_url,
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "prompt_strength": prompt_strength,
        "resolution": resolution,
        "cfg_scale": cfg_scale,
    }

    logger.info(f"[Kling] Submitting image2video: prompt={prompt[:60]}...")
    submit_resp = await client.post(submit_url, headers=headers, json=submit_payload)

    if submit_resp.status_code != 200:
        raise RuntimeError(f"Kling API error HTTP {submit_resp.status_code}: {submit_resp.text[:300]}")

    submit_data = submit_resp.json()
    if submit_data.get("code") != 0:
        raise RuntimeError(f"Kling API error: {submit_data.get('message', submit_data)}")

    task_id = submit_data.get("data", {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id in Kling response: {json.dumps(submit_data)[:200]}")

    logger.info(f"[Kling] Image2Video task submitted: task_id={task_id}")

    # 轮询任务状态
    start_time = time.time()
    query_url = f"{settings.kling_api_url}/videos/image2video/{task_id}"

    while time.time() - start_time < max_poll_time:
        await asyncio.sleep(poll_interval)

        poll_headers = _get_headers(access_key, secret_key)
        poll_resp = await client.get(query_url, headers=poll_headers)

        if poll_resp.status_code != 200:
            logger.warning(f"[Kling] Query error HTTP {poll_resp.status_code}, retrying...")
            continue

        poll_data = poll_resp.json()
        status = poll_data.get("data", {}).get("status", "")

        logger.info(f"[Kling] Task {task_id} status: {status}")

        if status == "completed":
            video_data = poll_data.get("data", {}).get("video", {})
            download_url = video_data.get("url") or video_data.get("download_url")
            if not download_url:
                raise RuntimeError(f"No download_url in Kling response: {json.dumps(poll_data)[:300]}")
            logger.info(f"[Kling] Video generated successfully: {download_url[:80]}...")
            return download_url

        elif status == "failed":
            raise RuntimeError(f"Kling video generation failed: {poll_data.get('message', poll_data)}")

    raise RuntimeError(f"Kling video generation timed out after {max_poll_time}s (task_id={task_id})")