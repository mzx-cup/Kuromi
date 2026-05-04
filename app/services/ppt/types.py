# -*- coding: utf-8 -*-
"""
PPT 生成类型定义
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class PPTElement:
    """PPT 元素基类"""
    type: str
    id: str = ""
    left: float = 0
    top: float = 0
    width: float = 100
    height: float = 100


@dataclass
class TextElement(PPTElement):
    """文本元素"""
    type: Literal["text"] = "text"
    content: str = ""
    fill: str = ""
    defaultColor: str = "#1E293B"
    defaultFontName: str = "Microsoft YaHei"
    opacity: float = 1


@dataclass
class ShapeElement(PPTElement):
    """形状元素"""
    type: Literal["shape"] = "shape"
    shape_name: str = "rectangle"
    path: str = ""
    fill: str = "#3B82F6"
    viewBox: list = field(default_factory=lambda: [0, 0, 100, 100])
    gradient: dict | None = None
    opacity: float = 1


@dataclass
class ImageElement(PPTElement):
    """图片元素"""
    type: Literal["image"] = "image"
    src: str = ""


@dataclass
class CodeElement(PPTElement):
    """代码元素"""
    type: Literal["code"] = "code"
    content: str = ""
    language: str = ""


@dataclass
class SlideBackground:
    """幻灯片背景"""
    type: str = "solid"  # solid, gradient
    color: str = "#F8FAFC"
    colors: list[str] | None = None


@dataclass
class SlideTheme:
    """幻灯片主题"""
    themeColors: list[str] = field(default_factory=lambda: ["#1E40AF", "#3B82F6"])
    fontColor: str = "#1E293B"
    backgroundColor: str = "#F8FAFC"
    fontName: str = "Microsoft YaHei"


@dataclass
class Slide:
    """幻灯片"""
    id: str = ""
    viewportSize: dict = field(default_factory=lambda: {"width": 1000, "height": 562.5})
    viewportRatio: float = 0.5625
    elements: list = field(default_factory=list)
    background: SlideBackground = field(default_factory=SlideBackground)
    theme: SlideTheme = field(default_factory=SlideTheme)
    remark: str = ""


@dataclass
class PPTGenerationRequest:
    """PPT 生成请求"""
    course_title: str = ""
    scene_title: str = ""
    scene_id: str = ""
    scene_type: str = "slide"  # slide, quiz, exercise, interactive
    content: list = field(default_factory=list)  # content items with sub_title, text, etc.
    design_style: str = "modern"  # modern, classic, playful, professional
    has_media_images: bool = False  # 是否有 AI 生成的图片需要嵌入
    media_image_aspect_ratio: str = "16:9"  # AI 图片的宽高比


@dataclass
class PPTGenerationResult:
    """PPT 生成结果"""
    success: bool = False
    slide: dict | None = None
    error: str = ""
