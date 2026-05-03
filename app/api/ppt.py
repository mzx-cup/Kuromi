# -*- coding: utf-8 -*-
"""
PPT 生成 API

POST /api/v2/ppt/generate — 使用 MiniMax 模型生成精美幻灯片
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.ppt import get_ppt_provider, PPTGenerationRequest

logger = logging.getLogger("starlearn.api.ppt")

router = APIRouter(prefix="/ppt", tags=["ppt"])


class PPTContentItem(BaseModel):
    """PPT 内容项"""
    sub_title: str = ""
    text: str = ""
    icon: str = "book"
    color_theme: str = "blue"
    code_snippet: str = ""
    image_url: str = ""


class PPTGenerateRequest(BaseModel):
    """PPT 生成请求"""
    course_title: str = ""
    scene_title: str = ""
    scene_id: str = ""
    scene_type: str = "slide"
    content: list[PPTContentItem] = []
    design_style: str = "modern"


class PPTGenerateResponse(BaseModel):
    """PPT 生成响应"""
    success: bool
    slide: dict | None = None
    error: str = ""


@router.post("/generate", response_model=PPTGenerateResponse)
async def generate_ppt(req: PPTGenerateRequest):
    """
    使用 MiniMax 大模型生成精美的 OpenMAIC 格式幻灯片。

    请求参数:
    - course_title: 课程标题
    - scene_title: 场景/章节标题
    - scene_type: 场景类型 (slide/quiz/exercise/interactive)
    - content: 内容项列表
    - design_style: 设计风格 (modern/classic/playful/professional/minimal)

    返回:
    - success: 是否成功
    - slide: OpenMAIC 格式的幻灯片 JSON
    - error: 错误信息
    """
    if not req.scene_title and not req.content:
        raise HTTPException(status_code=400, detail="scene_title or content is required")

    # 构造请求
    request = PPTGenerationRequest(
        course_title=req.course_title,
        scene_title=req.scene_title or "未命名幻灯片",
        scene_id=req.scene_id,
        scene_type=req.scene_type,
        content=[item.model_dump() for item in req.content],
        design_style=req.design_style,
    )

    # 调用生成服务
    provider = get_ppt_provider()
    result = await provider.generate(request)

    if result.success:
        logger.info(
            "PPT generated successfully: scene_title=%s, elements=%d",
            req.scene_title,
            len(result.slide.get("elements", [])) if result.slide else 0,
        )
    else:
        logger.error("PPT generation failed: %s", result.error)

    return PPTGenerateResponse(
        success=result.success,
        slide=result.slide,
        error=result.error,
    )
