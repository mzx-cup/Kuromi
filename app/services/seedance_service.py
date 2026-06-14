"""Seedance 2.0 视频生成 — 异步创建任务 → 轮询 → 下载到本地"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx

from app.services.ark_client import get_ark_client

logger = logging.getLogger("starlearn.seedance")

# 本地视频存储根目录
STORAGE_ROOT = Path(os.environ.get("STORAGE_DIR", "storage")) / "videos"

# 任务状态常量
STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"

_POLL_INTERVAL_SEC = 30  # 轮询间隔
_MAX_POLL_MINUTES = 30   # 最大等待分钟数


def _ensure_storage(sub_dir: str = "") -> Path:
    """确保视频存储目录存在并返回完整路径。"""
    dst = STORAGE_ROOT / sub_dir
    dst.mkdir(parents=True, exist_ok=True)
    return dst


def create_video_task(
    prompt: str,
    *,
    ratio: str = "16:9",
    duration: int = 5,
    reference_image_url: str | None = None,
    reference_video_url: str | None = None,
    generate_audio: bool = True,
    watermark: bool = True,
    model: str | None = None,
) -> str:
    """创建 Seedance 2.0 视频生成任务,返回 task_id。

    参数:
      prompt — 视频描述文字
      ratio — 宽高比,如 '16:9', '9:16', '1:1'
      duration — 视频长度(秒)
      reference_image_url / reference_video_url — 参考素材(可选,编辑模式)
      generate_audio — 是否同步生成音频
      watermark — 是否加水印
      model — 可覆盖模型 ID,默认读 .env ARK_VIDEO_MODEL
    """
    client = get_ark_client()
    model_id = model or os.environ.get(
        "ARK_VIDEO_MODEL", "doubao-seedance-2-0-260128"
    )

    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    if reference_image_url:
        content.append({
            "type": "image_url",
            "image_url": {"url": reference_image_url},
            "role": "reference_image",
        })
    if reference_video_url:
        content.append({
            "type": "video_url",
            "video_url": {"url": reference_video_url},
            "role": "reference_video",
        })

    result = client.content_generation.tasks.create(
        model=model_id,
        content=content,
        generate_audio=generate_audio,
        ratio=ratio,
        duration=duration,
        watermark=watermark,
    )
    logger.info("视频任务创建成功 task_id=%s", result.id)
    return result.id


def get_task(task_id: str) -> dict[str, Any]:
    """查询视频生成任务状态,返回原始 ContentGenerationTask dict。"""
    client = get_ark_client()
    task = client.content_generation.tasks.get(task_id=task_id)
    return {
        "id": task.id,
        "status": task.status,
        "video_url": getattr(task.content, "video_url", None) or "",
        "error": (
            {"code": task.error.code, "message": task.error.message}
            if task.error and task.error.code
            else None
        ),
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def poll_until_done(task_id: str, *, timeout_minutes: int = _MAX_POLL_MINUTES) -> dict[str, Any]:
    """同步轮询直至任务成功/失败,返回最终结果。

    适用于后台线程 / BackgroundTask,不阻塞 FastAPI event loop 时配合
    asyncio.to_thread 使用。
    """
    deadline = time.time() + timeout_minutes * 60
    last_status = ""

    while time.time() < deadline:
        info = get_task(task_id)
        status = info["status"]
        if status != last_status:
            logger.info("视频任务 %s 状态: %s", task_id, status)
            last_status = status

        if status == STATUS_SUCCEEDED:
            return info
        if status in (STATUS_FAILED, STATUS_CANCELLED):
            logger.warning("视频任务 %s 终态: %s error=%s", task_id, status, info.get("error"))
            return info

        # 未完成,等 _POLL_INTERVAL_SEC 后重试
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        time.sleep(min(_POLL_INTERVAL_SEC, remaining))

    # 超时
    logger.warning("视频任务 %s 轮询超时(%dmin)", task_id, timeout_minutes)
    return {"id": task_id, "status": "timeout", "video_url": "", "error": None}


def download_video(video_url: str, task_id: str, sub_dir: str = "") -> Path:
    """把视频 URL 下载到本地 storage/videos/, 返回本地路径。"""
    _ensure_storage(sub_dir)
    ext = ".mp4"  # Seedance 目前只输出 mp4
    local_path = STORAGE_ROOT / sub_dir / f"{task_id}{ext}"

    logger.info("下载视频 %s -> %s", video_url, local_path)
    resp = httpx.get(video_url, follow_redirects=True, timeout=300)
    resp.raise_for_status()
    local_path.write_bytes(resp.content)
    logger.info("视频下载完成 size=%d", len(resp.content))
    return local_path


def generate_video_sync(
    prompt: str,
    *,
    ratio: str = "16:9",
    duration: int = 5,
    sub_dir: str = "",
    reference_image_url: str | None = None,
    reference_video_url: str | None = None,
    generate_audio: bool = True,
    watermark: bool = True,
) -> dict[str, Any]:
    """创建 + 轮询 + 下载, 全同步, 适合后台任务。"""
    task_id = create_video_task(
        prompt=prompt,
        ratio=ratio,
        duration=duration,
        reference_image_url=reference_image_url,
        reference_video_url=reference_video_url,
        generate_audio=generate_audio,
        watermark=watermark,
    )
    result = poll_until_done(task_id)
    if result["status"] != STATUS_SUCCEEDED:
        return result

    local_path = download_video(result["video_url"], task_id, sub_dir)
    result["local_path"] = str(local_path)
    return result
