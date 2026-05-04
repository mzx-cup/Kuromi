# -*- coding: utf-8 -*-
"""
MiniMax PPT 生成 Provider

使用 MiniMax 大模型直接生成 OpenMAIC 格式的精美幻灯片。
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any

import httpx

from config import settings
from app.services.ppt.types import (
    PPTGenerationRequest,
    PPTGenerationResult,
    Slide,
    SlideBackground,
    SlideTheme,
)

logger = logging.getLogger("starlearn.ppt.minimax")


# ============================================================================
# OpenMAIC Slide Element Builders
# ============================================================================

VIEWPORT_W = 1000
VIEWPORT_H = 562.5
TITLE_H = 56


def clamp_coord(val: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, val))


def make_rounded_rect_path(w: float, h: float, r: float) -> str:
    wr = min(r, w / 2)
    hr = min(r, h / 2)
    return (
        f"M {wr} 0 "
        f"L {w - wr} 0 "
        f"Q {w} 0 {w} {hr} "
        f"L {w} {h - hr} "
        f"Q {w} {h} {w - wr} {h} "
        f"L {wr} {h} "
        f"Q 0 {h} 0 {h - hr} "
        f"L 0 {hr} "
        f"Q 0 0 {wr} 0 "
        f"Z"
    )


def make_gradient(colors: list[str], angle: float = 0) -> dict:
    return {
        "type": "linear",
        "colors": [
            {"color": colors[0], "pos": 0},
            {"color": colors[1], "pos": 1}
        ],
        "rotate": angle
    }


def make_title_bar(title: str, scene_id: str | int, bg_color: str = "#1E40AF") -> dict:
    return {
        "type": "shape",
        "id": f"el-{scene_id}-title-bar",
        "left": 0,
        "top": 0,
        "width": VIEWPORT_W,
        "height": TITLE_H,
        "shape_name": "rectangle",
        "path": make_rounded_rect_path(VIEWPORT_W, TITLE_H, 0),
        "fill": bg_color,
        "viewBox": [0, 0, VIEWPORT_W, TITLE_H],
    }


def make_title_text(title: str, scene_id: str | int) -> dict:
    return {
        "type": "text",
        "id": f"el-{scene_id}-title",
        "left": 20,
        "top": 0,
        "width": VIEWPORT_W - 40,
        "height": TITLE_H,
        "content": f'<h1 style="margin:0;font-size:24px;font-weight:700;color:#FFFFFF;text-align:center;line-height:{TITLE_H}px;">{title}</h1>',
        "fill": "transparent",
        "defaultColor": "#FFFFFF",
        "defaultFontName": "Microsoft YaHei",
    }


def make_card(
    item: dict,
    left: float,
    top: float,
    width: float,
    height: float,
    card_idx: int,
    scene_id: str | int,
    theme_colors: dict
) -> list[dict]:
    """生成一个内容卡片的所有元素"""
    elements = []

    theme_name = item.get("color_theme", "blue")
    theme = theme_colors.get(theme_name, theme_colors["blue"])
    card_radius = 12

    # 卡片背景
    bg_id = f"el-{scene_id}-card-{card_idx}-bg"
    elements.append({
        "type": "shape",
        "id": bg_id,
        "left": left,
        "top": top,
        "width": width,
        "height": height,
        "shape_name": "rectangle",
        "path": make_rounded_rect_path(width, height, card_radius),
        "fill": theme["hex"],
        "viewBox": [0, 0, width, height],
        "opacity": 0.95,
    })

    # 卡片标题
    sub_title = item.get("sub_title", "")
    icon = _get_icon(item.get("icon", "book"))
    if sub_title:
        title_h = 32
        title_y = top + 8
        elements.append({
            "type": "text",
            "id": f"el-{scene_id}-card-{card_idx}-title",
            "left": left + 12,
            "top": title_y,
            "width": width - 24,
            "height": title_h,
            "content": f'<strong style="color:{theme["text"]};font-size:14px;font-weight:600;">{icon} {sub_title}</strong>',
            "fill": "transparent",
            "defaultColor": theme["text"],
            "defaultFontName": "Microsoft YaHei",
        })
        body_top = top + title_h + 8
        body_h = height - title_h - 16
    else:
        body_top = top + 12
        body_h = height - 24

    # 内容区域
    text = item.get("text", "")
    code_snippet = item.get("code_snippet", "")
    image_url = item.get("image_url", "")

    has_code = code_snippet and str(code_snippet).strip()
    has_image = image_url and str(image_url).strip()

    if has_code and has_image:
        # 左侧文本，右侧代码和图片
        code_w = width * 0.5
        img_w = width - code_w - 16
        elements.append({
            "type": "text",
            "id": f"el-{scene_id}-card-{card_idx}-body",
            "left": left + 12,
            "top": body_top,
            "width": code_w - 12,
            "height": body_h * 0.55,
            "content": _parse_markdown(text, theme["text"]),
            "fill": "transparent",
            "defaultColor": theme["text"],
            "defaultFontName": "Microsoft YaHei",
        })
        elements.append({
            "type": "code",
            "id": f"el-{scene_id}-card-{card_idx}-code",
            "left": left + 12,
            "top": body_top + body_h * 0.55 + 4,
            "width": code_w - 12,
            "height": body_h * 0.45 - 4,
            "content": str(code_snippet),
            "language": "python",
        })
        elements.append({
            "type": "image",
            "id": f"el-{scene_id}-card-{card_idx}-img",
            "left": left + code_w + 8,
            "top": body_top,
            "width": img_w - 12,
            "height": body_h,
            "src": image_url,
        })
    elif has_code:
        # 上方文本，下方代码
        text_h = body_h * 0.4
        elements.append({
            "type": "text",
            "id": f"el-{scene_id}-card-{card_idx}-body",
            "left": left + 12,
            "top": body_top,
            "width": width - 24,
            "height": text_h,
            "content": _parse_markdown(text, theme["text"]),
            "fill": "transparent",
            "defaultColor": theme["text"],
            "defaultFontName": "Microsoft YaHei",
        })
        elements.append({
            "type": "code",
            "id": f"el-{scene_id}-card-{card_idx}-code",
            "left": left + 12,
            "top": body_top + text_h + 4,
            "width": width - 24,
            "height": body_h - text_h - 4,
            "content": str(code_snippet),
            "language": "python",
        })
    elif has_image:
        # 左侧文本，右侧图片
        txt_w = width * 0.55
        img_w = width - txt_w - 12
        elements.append({
            "type": "text",
            "id": f"el-{scene_id}-card-{card_idx}-body",
            "left": left + 12,
            "top": body_top,
            "width": txt_w - 12,
            "height": body_h,
            "content": _parse_markdown(text, theme["text"]),
            "fill": "transparent",
            "defaultColor": theme["text"],
            "defaultFontName": "Microsoft YaHei",
        })
        elements.append({
            "type": "image",
            "id": f"el-{scene_id}-card-{card_idx}-img",
            "left": left + txt_w + 4,
            "top": body_top,
            "width": img_w - 8,
            "height": body_h,
            "src": image_url,
        })
    else:
        # 仅文本
        elements.append({
            "type": "text",
            "id": f"el-{scene_id}-card-{card_idx}-body",
            "left": left + 12,
            "top": body_top,
            "width": width - 24,
            "height": body_h,
            "content": _parse_markdown(text, theme["text"]),
            "fill": "transparent",
            "defaultColor": theme["text"],
            "defaultFontName": "Microsoft YaHei",
        })

    return elements


def _parse_markdown(text: str, color: str) -> str:
    """简单的 Markdown 到 HTML 转换"""
    if not text:
        return ""
    html = str(text)
    # 标题
    html = html.replace("**", "")
    # 换行
    html = html.replace("\n", "<br>")
    # 行内代码
    import re
    html = re.sub(r"`([^`]+)`", r"<code style='background:#F1F5F9;padding:2px 6px;border-radius:4px;font-family:monospace;'>\\1</code>", html)
    return f'<div style="color:{color};font-size:13px;line-height:1.6;">{html}</div>'


def _get_icon(icon_name: str) -> str:
    icons = {
        "book": "📖",
        "lightbulb": "💡",
        "code": "💻",
        "check": "✅",
        "star": "⭐",
        "question": "❓",
        "warning": "⚠️",
        "info": "ℹ️",
    }
    return icons.get(icon_name, icons["book"])


# 前端 slide-v2-adapter.js 同步的 30 种主题色
THEME_COLORS = {
    # 基础色（1-15）
    "blue":   {"bg": "#DBEAFE", "text": "#1E40AF", "accent": "#3B82F6", "hex": "#DBEAFE"},
    "yellow": {"bg": "#FEF3C7", "text": "#92400E", "accent": "#F59E0B", "hex": "#FEF3C7"},
    "green":  {"bg": "#D1FAE5", "text": "#065F46", "accent": "#10B981", "hex": "#D1FAE5"},
    "purple": {"bg": "#EDE9FE", "text": "#5B21B6", "accent": "#8B5CF6", "hex": "#EDE9FE"},
    "orange": {"bg": "#FFF7ED", "text": "#9A3412", "accent": "#F97316", "hex": "#FFF7ED"},
    "cyan":   {"bg": "#CFFAFE", "text": "#164E63", "accent": "#06B6D4", "hex": "#CFFAFE"},
    "pink":   {"bg": "#FCE7F3", "text": "#831843", "accent": "#EC4899", "hex": "#FCE7F3"},
    "indigo": {"bg": "#E0E7FF", "text": "#3730A3", "accent": "#6366F1", "hex": "#E0E7FF"},
    "teal":   {"bg": "#CCFBF1", "text": "#115E59", "accent": "#14B8A6", "hex": "#CCFBF1"},
    "rose":   {"bg": "#FFE4E6", "text": "#9F1239", "accent": "#F43F5E", "hex": "#FFE4E6"},
    "amber":  {"bg": "#FFFBEB", "text": "#78350F", "accent": "#F59E0B", "hex": "#FFFBEB"},
    "lime":   {"bg": "#ECFCC5", "text": "#3F6212", "accent": "#84CC16", "hex": "#ECFCC5"},
    "sky":    {"bg": "#E0F2FE", "text": "#0C4A6E", "accent": "#0EA5E9", "hex": "#E0F2FE"},
    "violet": {"bg": "#F5F3FF", "text": "#4C1D95", "accent": "#8B5CF6", "hex": "#F5F3FF"},
    "slate":  {"bg": "#F1F5F9", "text": "#1E293B", "accent": "#64748B", "hex": "#F1F5F9"},
    # 扩展色（16-30）
    "crimson":  {"bg": "#FFE4E6", "text": "#9F1239", "accent": "#DC2626", "hex": "#FFE4E6"},
    "emerald":  {"bg": "#D1FAE5", "text": "#065F46", "accent": "#059669", "hex": "#D1FAE5"},
    "fuchsia":  {"bg": "#FCE7F3", "text": "#831843", "accent": "#D946EF", "hex": "#FCE7F3"},
    "gold":     {"bg": "#FFFBEB", "text": "#78350F", "accent": "#D97706", "hex": "#FFFBEB"},
    "gray":     {"bg": "#F3F4F6", "text": "#1F2937", "accent": "#6B7280", "hex": "#F3F4F6"},
    "aqua":     {"bg": "#CFFAFE", "text": "#164E63", "accent": "#0891B2", "hex": "#CFFAFE"},
    "lavender": {"bg": "#EDE9FE", "text": "#5B21B6", "accent": "#A78BFA", "hex": "#EDE9FE"},
    "coral":    {"bg": "#FFF7ED", "text": "#9A3412", "accent": "#FB923C", "hex": "#FFF7ED"},
    "navy":     {"bg": "#E0E7FF", "text": "#3730A3", "accent": "#4338CA", "hex": "#E0E7FF"},
    "mint":     {"bg": "#CCFBF1", "text": "#115E59", "accent": "#34D399", "hex": "#CCFBF1"},
    "peach":    {"bg": "#FCE7F3", "text": "#831843", "accent": "#FB7185", "hex": "#FCE7F3"},
    "rust":     {"bg": "#FFF7ED", "text": "#9A3412", "accent": "#EA580C", "hex": "#FFF7ED"},
    "sand":     {"bg": "#FEF3C7", "text": "#92400E", "accent": "#FCD34D", "hex": "#FEF3C7"},
    "sage":     {"bg": "#ECFCC5", "text": "#3F6212", "accent": "#65A30D", "hex": "#ECFCC5"},
    "wine":     {"bg": "#F5F3FF", "text": "#4C1D95", "accent": "#7C3AED", "hex": "#F5F3FF"},
}


# 语义颜色匹配表 - 根据内容关键词匹配主题色（支持30种颜色）
SEMANTIC_COLOR_MAP = {
    # 核心/基础/重要概念 - 使用蓝色
    "基础": "blue", "核心": "blue", "概念": "blue", "原理": "blue",
    "入门": "blue", "概述": "blue", "简介": "blue", "导论": "blue",

    # 警告/注意/危险 - 使用黄色/橙色
    "警告": "yellow", "注意": "yellow", "危险": "orange", "错误": "orange",
    "异常": "orange", "失败": "orange", "问题": "yellow", "警告": "amber",

    # 成功/完成/正确 - 使用绿色
    "成功": "green", "完成": "green", "正确": "green", "通过": "green",
    "验证": "green", "确认": "green", "优点": "green", "优势": "green",

    # 高级/特殊/重点 - 使用紫色
    "高级": "purple", "深入": "purple", "扩展": "purple", "特殊": "purple",
    "重点": "purple", "关键": "purple", "精华": "purple", "深度": "indigo",

    # 信息/提示/说明 - 使用蓝色系
    "信息": "blue", "提示": "blue", "说明": "blue", "解释": "blue",
    "定义": "blue", "介绍": "blue", "特点": "blue", "特性": "blue",

    # 代码/技术/实现 - 使用蓝色或青色
    "代码": "blue", "函数": "blue", "方法": "blue", "实现": "blue",
    "技术": "cyan", "算法": "cyan", "编程": "cyan", "开发": "cyan",
    "语法": "sky", "变量": "sky", "类型": "sky",

    # 创意/设计/艺术 - 使用粉色/紫红
    "创意": "pink", "设计": "pink", "艺术": "pink", "美学": "rose",
    "色彩": "violet", "绘制": "violet", "画": "rose",

    # 自然/环境/健康 - 使用绿色/青色
    "自然": "teal", "环境": "teal", "生态": "teal", "健康": "teal",
    "植物": "lime", "环保": "lime", "绿色": "lime",

    # 数据/统计/分析 - 使用青色/蓝色
    "数据": "cyan", "统计": "cyan", "分析": "cyan", "图表": "sky",
    "数字": "indigo", "指标": "indigo", "量化": "sky",

    # 时间/流程/步骤 - 使用蓝灰/石板色
    "时间": "slate", "流程": "slate", "步骤": "slate", "阶段": "slate",
    "顺序": "slate", "进度": "slate", "计划": "slate",
}


def match_semantic_color(text: str, fallback: str = "blue") -> str:
    """根据文本内容匹配语义化颜色"""
    if not text:
        return fallback

    text_lower = text.lower()

    # 优先匹配更具体的关键词
    priority_keywords = {
        "成功": "green", "完成": "green", "正确": "green", "通过": "green",
        "警告": "yellow", "注意": "yellow", "危险": "orange", "错误": "orange",
        "异常": "orange", "失败": "orange", "问题": "yellow",
    }

    for keyword, color in priority_keywords.items():
        if keyword in text_lower:
            return color

    # 通用关键词匹配
    for keyword, color in SEMANTIC_COLOR_MAP.items():
        if keyword in text_lower:
            return color

    return fallback


# ============================================================================
# MiniMax PPT Provider
# ============================================================================

class MiniMaxPPTProvider:
    provider_id = "minimax-ppt"

    SYSTEM_PROMPT = """你是一个专业的PPT幻灯片设计助手，负责生成精美的教学内容幻灯片。

## 你的任务
根据用户提供的课程内容，生成高质量的OpenMAIC格式幻灯片JSON。

## OpenMAIC 幻灯片格式规范

### 视图参数
- viewportSize: {"width": 1000, "height": 562.5}
- viewportRatio: 0.5625

### 背景设置
```json
{
  "background": {
    "type": "solid",  // 或 "gradient"
    "color": "#F8FAFC"
  }
}
```

### 元素类型

**1. shape (形状)** - 用于背景卡片、装饰元素
```json
{
  "type": "shape",
  "id": "unique-id",
  "left": 50,        // 左上角X (0-1000)
  "top": 80,        // 左上角Y (0-562.5)
  "width": 400,
  "height": 200,
  "shape_name": "rectangle",
  "path": "M 12 0 L 388 0 Q 400 0 400 12 L 400 188 Q 400 200 388 200 L 12 200 Q 0 200 0 188 L 0 12 Q 0 0 12 0 Z",
  "fill": "#EFF6FF",
  "viewBox": [0, 0, 400, 200],
  "gradient": {
    "type": "linear",
    "colors": [{"color": "#3B82F6", "pos": 0}, {"color": "#8B5CF6", "pos": 1}],
    "rotate": 45
  },
  "opacity": 0.95
}
```

**2. text (文本)** - 用于标题、正文
```json
{
  "type": "text",
  "id": "unique-id",
  "left": 50,
  "top": 80,
  "width": 400,
  "height": 40,
  "content": "<h1 style='color:#1E40AF;font-size:24px;'>标题</h1>",
  "fill": "transparent",
  "defaultColor": "#1E40AF",
  "defaultFontName": "Microsoft YaHei"
}
```

支持HTML格式：
- `<h1>` 主标题
- `<h2>` 副标题
- `<strong>` 粗体
- `<code>` 行内代码
- `<br>` 换行

**3. code (代码块)**
```json
{
  "type": "code",
  "id": "unique-id",
  "left": 500,
  "top": 120,
  "width": 450,
  "height": 350,
  "content": "print('Hello World')",
  "language": "python"
}
```

**4. image (图片)**
```json
{
  "type": "image",
  "id": "unique-id",
  "left": 500,
  "top": 120,
  "width": 450,
  "height": 300,
  "src": "https://example.com/image.png"
}
```

## 布局设计原则

### 1. 标题栏设计
- 顶部标题栏高度 56px
- 使用渐变色背景 (如 #1E40AF → #3B82F6)
- 白色文字居中

### 2. 内容卡片
- 圆角矩形卡片 (圆角12px)
- 使用主题色背景 (blue/yellow/green/purple/orange)
- 卡片之间间距 16px

### 3. 布局类型

**两栏布局 (two-column)**
- 第一行两个等宽卡片 (各约470px)
- 第二行一个全宽卡片

**网格布局 (grid-cards)**
- 2-3列网格
- 根据内容数量自适应

**标题+内容 (header-content)**
- 顶部大卡片作为引言/概述
- 下方多列详细内容

**引用高亮 (quote-highlight)**
- 顶部大引用区域
- 下方卡片详细说明

## 设计风格

### 配色方案
- Primary Blue: #1E40AF
- Accent Blue: #3B82F6
- Background: #F8FAFC
- Text Dark: #1E293B
- Text Light: #64748B

### 主题色（15种）
- Blue: bg=#DBEAFE, text=#1E40AF
- Yellow: bg=#FEF3C7, text=#92400E
- Green: bg=#D1FAE5, text=#065F46
- Purple: bg=#EDE9FE, text=#5B21B6
- Orange: bg=#FFF7ED, text=#9A3412
- Cyan: bg=#CFFAFE, text=#164E63
- Pink: bg=#FCE7F3, text=#831843
- Indigo: bg=#E0E7FF, text=#3730A3
- Teal: bg=#CCFBF1, text=#115E59
- Rose: bg=#FFE4E6, text=#9F1239
- Amber: bg=#FFFBEB, text=#78350F
- Lime: bg=#ECFCC5, text=#3F6212
- Sky: bg=#E0F2FE, text=#0C4A6E
- Violet: bg=#F5F3FF, text=#4C1D95
- Slate: bg=#F1F5F9, text=#1E293B

## 输出要求

1. 只输出JSON格式的幻灯片数据
2. 不要包含任何解释或说明
3. 确保元素坐标在有效范围内
4. 合理使用颜色对比保证可读性
5. 代码块使用深色背景 (#1E293B) 和等宽字体
6. **重要**：每个元素必须有唯一的ID，不要生成重复的标题栏或背景元素
7. **重要**：相邻的内容卡片必须使用不同的主题色，避免颜色一致性
8. **重要**：每个卡片只能有一个背景shape元素，不要重复定义

## 颜色使用规则

当内容项指定了配色主题时（如"blue", "purple"），必须使用对应的主题色。
**重要**：相邻的卡片必须使用不同的颜色！使用 color_theme 字段来确保颜色差异化。

## 布局类型（共14种）

**基础布局（5种）**：title-only, two-column, grid-cards, header-content, quote-highlight

**扩展布局（9种）**：center-focus, media-left, stats-row, timeline-steps, fullwidth-banner, comparison, three-column-cards, asymmetric-split, hero-center

## 图片友好型布局

当需要嵌入 AI 生成的图片时，推荐使用：
- media-left：图片在左侧，内容在右侧
- hero-center：顶部大图，中心聚焦
- fullwidth-banner：全宽横幅图片
- asymmetric-split：不对称分割，图片占大区域
- center-focus：中心聚焦，适合单图展示

这些布局为图片预留了充足空间。

## 示例输出

```json
{
  "id": "slide-1",
  "viewportSize": {"width": 1000, "height": 562.5},
  "viewportRatio": 0.5625,
  "background": {"type": "solid", "color": "#F8FAFC"},
  "elements": [
    // 标题栏背景
    {
      "type": "shape",
      "id": "el-1-title-bar",
      "left": 0, "top": 0, "width": 1000, "height": 56,
      "path": "...",
      "fill": "#1E40AF",
      "viewBox": [0, 0, 1000, 56]
    },
    // 标题文字
    {
      "type": "text",
      "id": "el-1-title",
      "left": 20, "top": 0, "width": 960, "height": 56,
      "content": "<h1 style='color:#FFF;...'>Java语言特性</h1>",
      "fill": "transparent",
      "defaultColor": "#FFFFFF"
    }
    // ... 更多元素
  ],
  "theme": {
    "themeColors": ["#1E40AF", "#3B82F6", "#EFF6FF"],
    "fontColor": "#1E293B",
    "backgroundColor": "#F8FAFC"
  }
}
```

请根据以下内容生成幻灯片："""

    USER_PROMPT_TEMPLATE = """## 课程信息
- 课程标题: {course_title}
- 场景标题: {scene_title}
- 场景类型: {scene_type}

## 可用的30种主题色
{blue_colors}

## 内容项
{content_items}

## 设计要求
- 风格: {design_style}
- 布局类型: {layout_type}
- 重要规则：
  1. 每张幻灯片最多使用5种主题色，相邻卡片必须使用不同颜色
  2. 同一课程中不同幻灯片之间，排版和颜色组合不能完全相同或高度相似
  3. 幻灯片之间应有明显的视觉差异（不同布局、不同配色、不同元素位置）
  4. 避免连续两张幻灯片使用相同或相似的布局结构和配色方案
{media_image_hint}

请生成一个精美的幻灯片JSON。"""

    LAYOUT_TYPES = [
        # 基础布局（1-8，对应内容数量1-8直接锁定）
        "title-only",      # 1项
        "two-column",      # 2项
        "quote-highlight", # 3项
        "stats-row",       # 4项
        "header-content",  # 5项
        "asymmetric-split",# 6项
        "timeline-steps",  # 7项
        "comparison",      # 8项
        # 扩展布局（9-25，用于9+项及风格池）
        "grid-cards",
        "center-focus",
        "media-left",
        "fullwidth-banner",
        "three-column-cards",
        "hero-center",
        "info-card",
        "feature-list",
        "hero-split",
        "numbered-list",
        "quote-card",
        "grid-highlight",
        "vertical-stack",
        "diagonal-split",
        "circle-accent",
        "sidebar-layout",
        "banner-strip",
    ]

    DESIGN_STYLES = [
        # 基础风格（1-6）
        "modern",       # 现代简约
        "classic",      # 经典稳重
        "playful",      # 活泼明亮
        "professional", # 专业商务
        "minimal",      # 极简留白
        "video",        # 视频优先
        # 扩展风格（7-15）
        "elegant",      # 优雅精致
        "bold",         # 大胆撞色
        "soft",         # 柔和温暖
        "tech",         # 科技感
        "creative",     # 创意艺术
        "nature",       # 自然清新
        "retro",        # 复古风格
        "luxury",       # 轻奢质感
        "kids",         # 童趣可爱
    ]

    # design_style 与主题色的映射关系（15种风格）
    STYLE_COLOR_PREFERENCES = {
        "modern":       ["blue", "cyan", "indigo", "purple", "sky"],
        "classic":      ["blue", "green", "purple", "slate", "indigo"],
        "playful":      ["pink", "amber", "lime", "orange", "yellow"],
        "professional": ["blue", "slate", "indigo", "teal", "cyan"],
        "minimal":      ["slate", "sky", "teal", "violet", "indigo"],
        "video":        ["slate", "indigo", "rose", "violet", "cyan"],
        "elegant":      ["violet", "rose", "gold", "slate", "fuchsia"],
        "bold":         ["crimson", "orange", "gold", "lime", "rose"],
        "soft":         ["peach", "sky", "lavender", "mint", "amber"],
        "tech":         ["navy", "slate", "cyan", "indigo", "emerald"],
        "creative":     ["fuchsia", "coral", "wine", "gold", "violet"],
        "nature":       ["sage", "mint", "emerald", "lime", "teal"],
        "retro":        ["coral", "amber", "rust", "gold", "sand"],
        "luxury":       ["wine", "gold", "navy", "slate", "crimson"],
        "kids":         ["peach", "coral", "sky", "lime", "yellow"],
    }

    # design_style 与布局的映射关系（15种风格）
    STYLE_LAYOUT_PREFERENCES = {
        "modern":       ["header-content", "center-focus", "grid-cards", "fullwidth-banner"],
        "classic":      ["two-column", "header-content", "quote-highlight", "comparison"],
        "playful":      ["grid-cards", "asymmetric-split", "timeline-steps", "three-column-cards"],
        "professional": ["header-content", "two-column", "stats-row", "center-focus"],
        "minimal":      ["title-only", "center-focus", "hero-center", "header-content"],
        "video":        ["hero-center", "fullwidth-banner", "media-left", "center-focus", "asymmetric-split"],
        "elegant":      ["quote-highlight", "center-focus", "hero-center", "grid-highlight"],
        "bold":         ["asymmetric-split", "diagonal-split", "grid-cards", "fullwidth-banner"],
        "soft":         ["vertical-stack", "info-card", "quote-card", "center-focus"],
        "tech":         ["header-content", "grid-cards", "feature-list", "banner-strip"],
        "creative":     ["hero-split", "circle-accent", "asymmetric-split", "sidebar-layout"],
        "nature":       ["feature-list", "numbered-list", "grid-cards", "vertical-stack"],
        "retro":        ["quote-card", "banner-strip", "numbered-list", "grid-highlight"],
        "luxury":       ["hero-center", "quote-highlight", "grid-highlight", "fullwidth-banner"],
        "kids":         ["numbered-list", "vertical-stack", "info-card", "grid-cards"],
    }

    # 图片友好型布局（当有AI图片时优先使用）
    IMAGE_FRIENDLY_LAYOUTS = [
        "media-left", "hero-center", "fullwidth-banner",
        "asymmetric-split", "center-focus"
    ]

    async def generate(
        self,
        request: PPTGenerationRequest,
    ) -> PPTGenerationResult:
        """
        使用 MiniMax API 生成 PPT 幻灯片
        """
        try:
            # 构造提示词
            content_items = self._format_content_items(request.content)
            layout_type = self._select_layout(request.content, request.scene_type, request.design_style)

            # 构建图片提示
            media_image_hint = ""
            if request.has_media_images:
                # 当有AI图片时，提供图片友好型布局建议和尺寸约束
                aspect_ratio = request.media_image_aspect_ratio
                if aspect_ratio == "16:9":
                    recommended_h = 400  # 宽度940时，16:9比例的高度
                elif aspect_ratio == "4:3":
                    recommended_h = 450
                elif aspect_ratio == "1:1":
                    recommended_h = 400
                else:
                    recommended_h = 400

                media_image_hint = f"""
## AI 图片嵌入提示
- 当前有 AI 生成的图片需要嵌入到幻灯片
- 图片宽高比: {aspect_ratio}
- 图片区域最小尺寸: 宽度≥400px，高度≥{recommended_h}px
- 推荐布局: {', '.join(self.IMAGE_FRIENDLY_LAYOUTS)}
- 如果使用其他布局，请确保有足够的空间展示图片"""

            user_prompt = self.USER_PROMPT_TEMPLATE.format(
                course_title=request.course_title,
                scene_title=request.scene_title,
                scene_type=request.scene_type,
                blue_colors=self._list_theme_colors(),
                content_items=content_items,
                design_style=request.design_style,
                layout_type=layout_type,
                media_image_hint=media_image_hint or "",
            )

            # 调用 MiniMax API
            slide_json = await self._call_minimax(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )

            # 去除 markdown 代码块包装
            slide_json = self._strip_markdown(slide_json)

            # 解析返回的 JSON
            slide = json.loads(slide_json)

            # 验证和修复 slide
            slide = self._validate_slide(slide, request.scene_title, request.scene_id)

            # 合成 actions (speech + spotlight + laser 序列)
            slide["actions"] = self._synthesize_actions(slide, request.content, request.scene_id)

            return PPTGenerationResult(success=True, slide=slide)

        except json.JSONDecodeError as e:
            logger.error("Failed to parse PPT JSON: %s", e)
            return PPTGenerationResult(success=False, error=f"JSON解析失败: {e}")
        except Exception as e:
            logger.error("PPT generation failed: %s", e)
            return PPTGenerationResult(success=False, error=str(e))

    def _list_theme_colors(self) -> str:
        """将30种主题色格式化为提示词文本"""
        lines = []
        for name, colors in THEME_COLORS.items():
            lines.append(f"- {name}: bg={colors['bg']}, text={colors['text']}, accent={colors['accent']}")
        return "\n".join(lines)

    def _format_content_items(self, content: list) -> str:
        """格式化内容项"""
        if not content:
            return "（无具体内容）"

        lines = []
        used_colors = set()

        for i, item in enumerate(content):
            # 自动匹配语义化颜色
            title = item.get("sub_title", "")
            text = item.get("text", "")
            combined_text = f"{title} {text}"

            # 匹配语义颜色
            semantic_color = match_semantic_color(combined_text, fallback=None)
            if semantic_color and semantic_color not in used_colors:
                item["color_theme"] = semantic_color
                used_colors.add(semantic_color)
            elif not item.get("color_theme"):
                # 如果已用或无匹配，使用差异化的默认颜色（15色循环）
                all_colors = list(THEME_COLORS.keys())
                for c in all_colors:
                    if c not in used_colors:
                        item["color_theme"] = c
                        used_colors.add(c)
                        break

            lines.append(f"\n### 项目 {i+1}")
            if item.get("sub_title"):
                lines.append(f"- 标题: {item['sub_title']}")
            if item.get("text"):
                lines.append(f"- 内容: {item['text'][:200]}...")
            if item.get("code_snippet"):
                lines.append(f"- 代码: {str(item['code_snippet'])[:100]}...")
            if item.get("icon"):
                lines.append(f"- 图标: {item['icon']}")
            if item.get("color_theme"):
                lines.append(f"- 配色主题: {item['color_theme']} (请勿更改)")


        return "\n".join(lines)

    def _select_layout(self, content: list, scene_type: str, design_style: str = "modern") -> str:
        """根据内容数量直接锁定布局（1-8项各自对应不同布局，样式差异最大化）"""
        if scene_type == "quiz":
            return "grid-cards"

        count = len(content)

        # 1-8项直接锁定不同布局，样式差异最大化
        if count == 1:
            return "title-only"
        elif count == 2:
            return "two-column"
        elif count == 3:
            return "quote-highlight"
        elif count == 4:
            return "stats-row"
        elif count == 5:
            return "header-content"
        elif count == 6:
            return "asymmetric-split"
        elif count == 7:
            return "timeline-steps"
        elif count == 8:
            return "comparison"

        # 9项及以上使用多内容布局池（从25种布局中排除已锁定的8种）
        multi_content_layouts = [
            l for l in [
                # 已锁定布局之外的扩展布局
                "grid-cards", "center-focus", "media-left", "fullwidth-banner",
                "three-column-cards", "hero-center", "info-card", "feature-list",
                "hero-split", "numbered-list", "quote-card", "grid-highlight",
                "vertical-stack", "diagonal-split", "circle-accent", "sidebar-layout", "banner-strip",
                # 保留部分已锁定布局作为回退
                "header-content", "stats-row", "two-column", "timeline-steps", "comparison",
            ] if l in self.LAYOUT_TYPES
        ]
        return random.choice(multi_content_layouts)

    def _strip_markdown(self, text: str) -> str:
        """去除 markdown 代码块包装"""
        import re
        # 去除 ```json ... ``` 或 ``` ... ``` 包装
        text = text.strip()
        match = re.match(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text

    async def _call_minimax(
        self,
        system_prompt: str,
        user_prompt: str,
        retry_count: int = 3,
    ) -> str:
        """调用 MiniMax API，带重试机制"""
        last_error = None

        for attempt in range(retry_count):
            try:
                url = f"{settings.minimax_api_url}/text/chatcompletion_v2"
                headers = {
                    "Authorization": f"Bearer {settings.minimax_api_key}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "model": settings.minimax_model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4096,
                }

                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(url, headers=headers, json=payload)

                    if response.status_code != 200:
                        raise RuntimeError(
                            f"MiniMax API error HTTP {response.status_code}: {response.text[:500]}"
                        )

                    data = response.json()
                    choices = data.get("choices", [])
                    if not choices:
                        raise RuntimeError("No choices returned from MiniMax API")

                    content = choices[0].get("message", {}).get("content", "")

                    # 检查返回内容是否为空
                    if not content or not content.strip():
                        logger.warning(f"MiniMax returned empty content, attempt {attempt + 1}/{retry_count}")
                        last_error = "Empty response from MiniMax API"
                        await asyncio.sleep(1)
                        continue

                    return content

            except json.JSONDecodeError as e:
                last_error = f"JSON decode error: {e}"
                logger.warning(f"MiniMax JSON decode error, attempt {attempt + 1}/{retry_count}: {e}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"MiniMax API error, attempt {attempt + 1}/{retry_count}: {e}")

            if attempt < retry_count - 1:
                await asyncio.sleep(2)

        # 所有重试都失败
        raise RuntimeError(f"MiniMax API failed after {retry_count} attempts. Last error: {last_error}")

    def _validate_slide(self, slide: dict, fallback_title: str, scene_id: str = "") -> dict:
        """验证和修复 slide 数据"""
        # 确保必要字段存在
        if "id" not in slide:
            slide["id"] = f"slide-{random.randint(1000, 9999)}"

        # 保存 scene_id 用于前端匹配
        if scene_id:
            slide["scene_id"] = scene_id

        if "viewportSize" not in slide:
            slide["viewportSize"] = {"width": VIEWPORT_W, "height": VIEWPORT_H}

        if "viewportRatio" not in slide:
            slide["viewportRatio"] = VIEWPORT_H / VIEWPORT_W

        if "background" not in slide:
            slide["background"] = {"type": "solid", "color": "#F8FAFC"}

        if "elements" not in slide:
            slide["elements"] = []

        if "theme" not in slide:
            slide["theme"] = {
                "themeColors": ["#1E40AF", "#3B82F6", "#EFF6FF"],
                "fontColor": "#1E293B",
                "backgroundColor": "#F8FAFC",
            }

        # 去重和修复元素
        validated_elements = []
        seen_ids = set()
        title_bar_count = 0

        for el in slide.get("elements", []):
            if not isinstance(el, dict) or "type" not in el:
                continue

            el_id = el.get("id", "")

            # 跳过完全重复的 ID
            if el_id in seen_ids:
                continue
            seen_ids.add(el_id)

            # 标题栏去重 - 保留第一个
            if "title" in el_id.lower() and "bar" in el_id.lower():
                title_bar_count += 1
                if title_bar_count > 1:
                    continue

            # 确保坐标在有效范围内
            el["left"] = clamp_coord(el.get("left", 0), 0, VIEWPORT_W - 1)
            el["top"] = clamp_coord(el.get("top", 0), 0, VIEWPORT_H - 1)
            el["width"] = clamp_coord(el.get("width", 100), 1, VIEWPORT_W)
            el["height"] = clamp_coord(el.get("height", 100), 1, VIEWPORT_H)

            # 确保不超出边界
            if el["left"] + el["width"] > VIEWPORT_W:
                el["width"] = VIEWPORT_W - el["left"]
            if el["top"] + el["height"] > VIEWPORT_H:
                el["height"] = VIEWPORT_H - el["top"]

            # 修复 shape 元素：如果同时有 fill 和 gradient，只保留 gradient
            if el.get("type") == "shape" and el.get("gradient") and el.get("fill"):
                # 渐变优先，但如果 fill 是纯色且 gradient 也有纯色版本，移除 fill
                if isinstance(el.get("fill"), str) and el["fill"].startswith("#"):
                    el["fill"] = el.get("gradient", {}).get("colors", [{}])[0].get("color", "#3B82F6")

            validated_elements.append(el)

        # 按 top 和 left 排序，确保元素按从上到下、从左到右的顺序渲染
        validated_elements.sort(key=lambda e: (e.get("top", 0), e.get("left", 0)))

        slide["elements"] = validated_elements
        return slide

    def _synthesize_actions(
        self, slide: dict, content: list, scene_id: str = ""
    ) -> list[dict]:
        """
        从幻灯片元素和内容项合成 action 序列。

        为每个内容卡片生成 interleaved speech + spotlight 动作，
        包含代码的卡片额外添加 laser 动作。

        格式匹配 openmaic-slide-player.js 的 normalizeActions:
          {type: "speech", text: "..."}
          {type: "spotlight", elementId: "el-...", duration: 4000}
          {type: "laser", elementId: "el-...", duration: 3000}
        """
        if not content:
            return []

        elements = slide.get("elements", [])
        element_ids = {el.get("id", "") for el in elements}
        actions = []

        # 场景标题 speech（如果有标题元素）
        title_el_id = f"el-{scene_id}-title-bar" if scene_id else None
        has_title = title_el_id and title_el_id in element_ids

        for idx, item in enumerate(content):
            sub_title = item.get("sub_title", "")
            text = item.get("text", "")
            code_snippet = item.get("code_snippet", "")

            # 构造语音文本
            speech_parts = []
            if sub_title:
                speech_parts.append(sub_title)
            if text:
                # 截断过长文本，保持语音流畅
                speech_parts.append(text[:500])
            speech_text = "。".join(speech_parts) if speech_parts else ""

            if not speech_text and not code_snippet:
                continue

            # 1) speech action
            if speech_text:
                actions.append({
                    "type": "speech",
                    "text": speech_text,
                })

            # 2) spotlight — 高亮卡片背景或正文区域
            bg_id = f"el-{scene_id}-card-{idx}-bg" if scene_id else None
            body_id = f"el-{scene_id}-card-{idx}-body" if scene_id else None

            spotlight_target = None
            if bg_id and bg_id in element_ids:
                spotlight_target = bg_id
            elif body_id and body_id in element_ids:
                spotlight_target = body_id

            if spotlight_target:
                actions.append({
                    "type": "spotlight",
                    "elementId": spotlight_target,
                    "duration": 4000,
                })

            # 3) laser — 指向代码块
            if code_snippet and str(code_snippet).strip():
                code_id = f"el-{scene_id}-card-{idx}-code" if scene_id else None
                if code_id and code_id in element_ids:
                    actions.append({
                        "type": "laser",
                        "elementId": code_id,
                        "duration": 3000,
                    })

        # 如果只有标题没有卡片内容，至少为标题栏添加 spotlight
        if not actions and has_title:
            actions.append({
                "type": "spotlight",
                "elementId": title_el_id,
                "duration": 3000,
            })

        return actions


# 单例
_provider = None


def get_ppt_provider() -> MiniMaxPPTProvider:
    global _provider
    if _provider is None:
        _provider = MiniMaxPPTProvider()
    return _provider
