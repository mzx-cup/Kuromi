"""火山方舟 Seedance (视频) + Seedream (图片) API

POST   /api/seed/video           -> 创建视频生成任务, 返回 task_id
GET    /api/seed/video/{task_id} -> 查状态 + 自动下载 (succeeded 时)
GET    /api/seed/video/file/{task_id} -> 播放本地视频文件

POST   /api/seed/image           -> 同步生成图片, 返回本地 URL
GET    /api/seed/image/file/{filename} -> 获取图片文件
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.seedance_service import (
    STORAGE_ROOT as VIDEO_STORAGE,
    create_video_task,
    get_task,
    download_video,
    STATUS_SUCCEEDED,
)
from app.services.seedream_service import generate_image

logger = logging.getLogger("starlearn.seed_media")
router = APIRouter(prefix="/api/seed")


# ── 请求 / 响应模型 ──


class VideoCreateRequest(BaseModel):
    prompt: str
    ratio: str = "16:9"
    duration: int = 5
    generate_audio: bool = True
    watermark: bool = True
    reference_image_url: str | None = None
    reference_video_url: str | None = None


class VideoCreateResponse(BaseModel):
    code: int = 200
    data: dict


class VideoStatusResponse(BaseModel):
    code: int = 200
    data: dict


class ImageGenerateRequest(BaseModel):
    prompt: str
    size: str = "1024x1024"
    watermark: bool = False
    sub_dir: str = ""


class ImageGenerateResponse(BaseModel):
    code: int = 200
    data: dict


# ── 视频: 创建任务 ──


@router.post("/video", response_model=VideoCreateResponse)
async def create_video(req: VideoCreateRequest):
    try:
        task_id = create_video_task(
            prompt=req.prompt,
            ratio=req.ratio,
            duration=req.duration,
            reference_image_url=req.reference_image_url,
            reference_video_url=req.reference_video_url,
            generate_audio=req.generate_audio,
            watermark=req.watermark,
        )
        return VideoCreateResponse(data={"task_id": task_id, "status": "queued"})
    except Exception as e:
        logger.exception("创建视频任务失败")
        raise HTTPException(status_code=502, detail=str(e))


# ── 视频: 查状态 (当 succeeded 时自动下载到本地) ──


@router.get("/video/{task_id}", response_model=VideoStatusResponse)
async def video_status(task_id: str):
    """查任务状态, 当 succeeded 且未下载时自动下载到本地。"""
    try:
        info = get_task(task_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    # 如果成功且有 video_url 且还没下载, 则自动下载
    if info["status"] == STATUS_SUCCEEDED and info.get("video_url"):
        local_path = VIDEO_STORAGE / f"{task_id}.mp4"
        if not local_path.exists():
            try:
                download_video(info["video_url"], task_id)
            except Exception as e:
                logger.warning("视频下载失败 task_id=%s: %s", task_id, e)
                # 下载失败不阻塞, 让前端可以重试
                info["download_error"] = str(e)

        if local_path.exists():
            info["local_url"] = f"/api/seed/video/file/{task_id}"

    return VideoStatusResponse(data=info)


# ── 视频: 播放本地文件 ──


@router.get("/video/file/{task_id}")
async def serve_video(task_id: str):
    path = VIDEO_STORAGE / f"{task_id}.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="视频文件不存在或尚未生成完成")
    return FileResponse(str(path), media_type="video/mp4", filename=f"{task_id}.mp4")


# ── 图片: 同步生成 ──


@router.post("/image", response_model=ImageGenerateResponse)
async def generate(req: ImageGenerateRequest):
    try:
        result = generate_image(
            prompt=req.prompt,
            size=req.size,
            watermark=req.watermark,
            sub_dir=req.sub_dir,
        )
        if result["status"] != "succeeded":
            raise HTTPException(status_code=502, detail=result.get("error", "图片生成失败"))

        # 转成可访问的 URL
        local_path = result["local_path"]
        filename = Path(local_path).name
        result["url"] = f"/api/seed/image/file/{filename}"
        return ImageGenerateResponse(data=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("图片生成失败")
        raise HTTPException(status_code=502, detail=str(e))


# ── 图片: 获取文件 ──


@router.get("/image/file/{filename:path}")
async def serve_image(filename: str):
    from app.services.seedream_service import STORAGE_ROOT as IMG_STORAGE
    path = IMG_STORAGE / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="图片文件不存在")
    return FileResponse(str(path))
