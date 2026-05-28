# -*- coding: utf-8 -*-
"""
MiniMax PPT 生成 Provider — 编程教学专用

使用 MiniMax 大模型直接生成 OpenMAIC 格式的精美幻灯片。
针对编程学习场景优化：代码展示、终端风格、API 文档等专用布局。
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
)

logger = logging.getLogger("starlearn.ppt.minimax")

# ============================================================================
# 视图常量
# ============================================================================

VIEWPORT_W = 1000
VIEWPORT_H = 562.5
TITLE_H = 56


def clamp_coord(val: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, val))


# ============================================================================
# MiniMax PPT Provider — 编程教学专用
# ============================================================================

class MiniMaxPPTProvider:
    provider_id = "minimax-ppt"

    SYSTEM_PROMPT = """你是一个专业的编程教学PPT幻灯片设计助手。你的任务是根据课程内容生成精美的OpenMAIC格式幻灯片JSON。

## 平台定位
这是一个编程学习平台，所有课程都是编程/计算机相关内容。幻灯片设计必须专业、清晰、适合代码展示。

## OpenMAIC 幻灯片格式规范

### 视图参数
- viewportSize: {"width": 1000, "height": 562.5}
- viewportRatio: 0.5625

### 背景设置
```json
{
  "background": {
    "type": "solid",
    "color": "#0F172A"
  }
}
```
推荐使用深色背景（#0F172A 深蓝灰）配合亮色卡片，营造科技感和专业编程氛围。

### 元素类型

**1. shape (形状)** — 背景卡片、装饰线条
```json
{
  "type": "shape",
  "id": "unique-id",
  "left": 50, "top": 80, "width": 400, "height": 200,
  "shape_name": "rectangle",
  "path": "M 12 0 L 388 0 Q 400 0 400 12 L 400 188 Q 400 200 388 200 L 12 200 Q 0 200 0 188 L 0 12 Q 0 0 12 0 Z",
  "fill": "#1E293B",
  "viewBox": [0, 0, 400, 200],
  "opacity": 0.95
}
```

**2. text (文本)** — 标题、正文、说明
```json
{
  "type": "text",
  "id": "unique-id",
  "left": 50, "top": 80, "width": 400, "height": 40,
  "content": "<h1 style='color:#E2E8F0;font-size:24px;font-weight:700;'>标题</h1>",
  "fill": "transparent",
  "defaultColor": "#E2E8F0",
  "defaultFontName": "Microsoft YaHei"
}
```

支持HTML格式：`<h1>` `<h2>` `<strong>` `<code>` `<br>` `<span>`

**3. code (代码块)** — 展示编程代码
```json
{
  "type": "code",
  "id": "unique-id",
  "left": 500, "top": 120, "width": 450, "height": 350,
  "content": "def hello():\\n    print('Hello World')",
  "language": "python"
}
```
代码块必须使用深色背景区域包裹（通过 shape），背景色 #0D1117 或 #1E1E1E，与整体深色主题协调。

**4. image (图片)** — 示意图、截图
```json
{
  "type": "image",
  "id": "unique-id",
  "left": 500, "top": 120, "width": 450, "height": 300,
  "src": "https://example.com/image.png"
}
```

## 编程教学布局规范

### 通用设计原则
1. **深色主题优先**：背景使用 #0F172A，卡片使用 #1E293B，文字使用 #E2E8F0
2. **代码高亮区**：代码块必须有独立的深色背景卡片（#0D1117），与内容区明显区分
3. **字体层级**：标题 22-26px，正文 14-16px，代码 13-14px（等宽字体）
4. **间距规范**：元素之间至少 16px 间距，卡片内边距 16-20px
5. **配色克制**：每张幻灯片最多 3 种主色，避免花哨。推荐色板：
   - 主色：#3B82F6（蓝）
   - 强调：#10B981（绿）#F59E0B（琥珀）
   - 文字：#E2E8F0（浅灰白）#94A3B8（次要文字）
   - 危险/错误：#EF4444（红）

### 布局类型（编程专用）

**code-showcase（代码展示）**
- 左侧 40%：概念说明文字区
- 右侧 60%：大代码块区域，带深色背景
- 适用于：讲解具体代码实现、函数用法

**terminal-style（终端风格）**
- 全宽或大面积终端模拟区域
- 顶部有命令提示符装饰条（绿色圆点 + 标题）
- 内容使用等宽字体，白色/绿色文字
- 适用于：命令行操作、CLI工具教学

**concept-code（概念+代码对照）**
- 上方：核心概念说明（1-2句话）
- 下方左右分栏：左侧文字要点，右侧对应代码示例
- 适用于：语法讲解、概念与实现对照

**api-doc（API文档）**
- 顶部：函数签名（大字号等宽字体，醒目展示）
- 中部：参数表格（参数名 | 类型 | 说明）
- 底部：返回值 + 示例代码
- 适用于：讲解函数/类/接口

**step-by-step（步骤教学）**
- 顶部标题 + 步骤编号（大号数字 01/02/03）
- 每个步骤配简短说明和对应代码片段
- 步骤之间用细线分隔
- 适用于：分步教程、操作流程

**header-content（标题内容）**
- 顶部标题栏（全宽，深色渐变）
- 下方 2-3 列等宽卡片展示要点
- 适用于：概述页、知识点归纳

**two-column（两栏对比）**
- 左右两栏等宽卡片
- 可对比：正确 vs 错误写法、Python2 vs Python3、Before vs After
- 适用于：对比教学、最佳实践

**grid-cards（卡片网格）**
- 2x2 或 3x2 网格布局
- 每张卡片一个小知识点
- 适用于：多个并列概念（如数据类型、运算符）

**comparison（对比布局）**
- 左右对比，中间用分隔线
- 左侧绿色（推荐），右侧红色（不推荐）
- 适用于：正反例对比、常见错误

**title-only（标题页）**
- 全屏大标题居中
- 副标题在下方
- 可配装饰性代码片段作为背景
- 适用于：章节开头、课程标题页

## 代码展示规范（CRITICAL）
1. 代码块必须使用 `type: "code"` 元素，不要放在 text 里
2. 代码区域要有独立背景 shape，颜色 #0D1117 或 #161B22
3. 代码字体大小 13-14px，行高 1.5
4. 关键行可用注释或不同颜色标注（在 content 中用 HTML 标签）
5. 代码左侧预留 4-8px 内边距，模拟编辑器效果
6. 长代码要截断或折叠，确保在视口内完整显示

## 输出要求
1. 只输出JSON格式的幻灯片数据，不要任何解释
2. 每个元素必须有唯一的ID
3. 确保元素坐标在 [0, 1000] x [0, 562.5] 范围内
4. 元素不重叠、不溢出视口
5. 保持深色科技风格，配色克制专业

请根据以下内容生成幻灯片："""

    USER_PROMPT_TEMPLATE = """## 课程信息
- 课程标题: {course_title}
- 场景标题: {scene_title}
- 场景类型: {scene_type}

## 内容项
{content_items}

## 设计要求
- 风格: {design_style}
- 布局类型: {layout_type}
- 重要规则：
  1. 使用深色科技风格（背景 #0F172A，卡片 #1E293B）
  2. 代码块必须有独立的深色背景区域
  3. 配色克制，每张幻灯片不超过 3 种主色
  4. 文字与背景对比度足够，确保可读性
  5. 元素间距至少 16px，不拥挤
{media_image_hint}

请生成一个精美的编程教学幻灯片JSON。"""

    # 编程教学专用布局（10种，精简实用）
    LAYOUT_TYPES = [
        "title-only",       # 标题页
        "header-content",   # 标题+内容卡片
        "two-column",       # 两栏对比
        "code-showcase",    # 代码展示（左文右码）
        "terminal-style",   # 终端风格
        "concept-code",     # 概念+代码对照
        "api-doc",          # API文档
        "step-by-step",     # 步骤教学
        "grid-cards",       # 卡片网格
        "comparison",       # 正反对比
    ]

    # 编程场景布局选择映射
    LAYOUT_BY_CONTENT = {
        "code": ["code-showcase", "concept-code", "terminal-style"],
        "command": ["terminal-style", "code-showcase"],
        "function": ["api-doc", "code-showcase", "concept-code"],
        "class": ["api-doc", "concept-code"],
        "step": ["step-by-step", "grid-cards"],
        "compare": ["comparison", "two-column"],
        "overview": ["header-content", "grid-cards"],
        "intro": ["title-only", "header-content"],
    }

    # 编程风格定义
    DESIGN_STYLES = [
        "dark-tech",      # 深色科技（默认，适合代码）
        "modern",         # 现代简约
        "minimal",        # 极简留白
        "professional",   # 专业商务
    ]

    # 风格配色
    STYLE_THEMES = {
        "dark-tech": {
            "bg": "#0F172A",
            "card": "#1E293B",
            "code_bg": "#0D1117",
            "text": "#E2E8F0",
            "text_secondary": "#94A3B8",
            "accent": "#3B82F6",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
        "modern": {
            "bg": "#F8FAFC",
            "card": "#FFFFFF",
            "code_bg": "#1E293B",
            "text": "#1E293B",
            "text_secondary": "#64748B",
            "accent": "#3B82F6",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
        "minimal": {
            "bg": "#FFFFFF",
            "card": "#F8FAFC",
            "code_bg": "#0F172A",
            "text": "#0F172A",
            "text_secondary": "#64748B",
            "accent": "#0EA5E9",
            "success": "#22C55E",
            "warning": "#EAB308",
            "error": "#DC2626",
        },
        "professional": {
            "bg": "#F1F5F9",
            "card": "#FFFFFF",
            "code_bg": "#1E293B",
            "text": "#334155",
            "text_secondary": "#64748B",
            "accent": "#6366F1",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
    }

    def __init__(self):
        self._layout_history: list[str] = []
        self._style_history: list[str] = []

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
            layout_type = self._select_layout(request.content, request.scene_type)
            design_style = self._select_design_style(request.content)

            # 构建图片提示
            media_image_hint = ""
            if request.has_media_images:
                media_image_hint = (
                    f"\n- 当前有 AI 生成的图片需要嵌入"
                    f"\n- 图片宽高比: {request.media_image_aspect_ratio}"
                    f"\n- 推荐布局: header-content, grid-cards"
                    f"\n- 图片区域最小尺寸: 宽度≥300px，高度≥200px"
                )

            user_prompt = self.USER_PROMPT_TEMPLATE.format(
                course_title=request.course_title,
                scene_title=request.scene_title,
                scene_type=request.scene_type,
                content_items=content_items,
                design_style=design_style,
                layout_type=layout_type,
                media_image_hint=media_image_hint,
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

            # 注入 theme 配色（确保风格一致）
            slide = self._inject_theme(slide, design_style)

            # 合成 actions
            slide["actions"] = self._synthesize_actions(slide, request.content, request.scene_id)

            return PPTGenerationResult(success=True, slide=slide)

        except json.JSONDecodeError as e:
            logger.error("Failed to parse PPT JSON: %s", e)
            return PPTGenerationResult(success=False, error=f"JSON解析失败: {e}")
        except Exception as e:
            logger.error("PPT generation failed: %s", e)
            return PPTGenerationResult(success=False, error=str(e))

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _select_design_style(self, content: list) -> str:
        """根据内容选择设计风格"""
        # 默认 dark-tech，如果有大量代码则保持 dark-tech
        has_code = any(
            item.get("code_snippet") or "代码" in item.get("text", "")
            for item in content
        )
        if has_code:
            return "dark-tech"
        return random.choice(["dark-tech", "modern", "minimal"])

    def _select_layout(self, content: list, scene_type: str) -> str:
        """智能选择布局：根据内容特征匹配最合适的编程教学布局"""
        if scene_type == "quiz":
            return "grid-cards"

        # 分析内容特征
        text_combined = " ".join(
            f"{item.get('sub_title', '')} {item.get('text', '')}"
            for item in content
        ).lower()

        has_code = any(item.get("code_snippet") for item in content)
        has_command = any(k in text_combined for k in ["命令", "cmd", "terminal", "shell", "bash", "git ", "npm ", "pip "])
        has_function = any(k in text_combined for k in ["函数", "方法", "def ", "function", "api", "参数", "返回值"])
        has_class = any(k in text_combined for k in ["类", "class ", "面向对象", "继承", "封装"])
        has_step = any(k in text_combined for k in ["步骤", "第一步", "首先", "然后", "接着", "最后"])
        has_compare = any(k in text_combined for k in ["对比", "区别", "vs", "versus", "正确", "错误", "不要"])

        candidates = []
        if has_command:
            candidates.extend(self.LAYOUT_BY_CONTENT["command"])
        elif has_code:
            candidates.extend(self.LAYOUT_BY_CONTENT["code"])
        if has_function:
            candidates.extend(self.LAYOUT_BY_CONTENT["function"])
        if has_class:
            candidates.extend(self.LAYOUT_BY_CONTENT["class"])
        if has_step:
            candidates.extend(self.LAYOUT_BY_CONTENT["step"])
        if has_compare:
            candidates.extend(self.LAYOUT_BY_CONTENT["compare"])

        # 去重并过滤未使用过的布局（确保视觉多样性）
        candidates = list(dict.fromkeys(candidates))
        unused = [c for c in candidates if c not in self._layout_history]

        if unused:
            choice = random.choice(unused)
        elif candidates:
            choice = random.choice(candidates)
        else:
            # 默认池
            default_pool = ["header-content", "grid-cards", "two-column", "title-only"]
            unused_default = [c for c in default_pool if c not in self._layout_history]
            choice = random.choice(unused_default) if unused_default else random.choice(default_pool)

        self._layout_history.append(choice)
        # 只保留最近 5 个历史，避免过度限制
        self._layout_history = self._layout_history[-5:]
        return choice

    def _format_content_items(self, content: list) -> str:
        """格式化内容项，突出编程特征"""
        if not content:
            return "（无具体内容）"

        lines = []
        for i, item in enumerate(content):
            lines.append(f"\n### 项目 {i+1}")
            if item.get("sub_title"):
                lines.append(f"- 标题: {item['sub_title']}")
            if item.get("text"):
                lines.append(f"- 内容: {item['text'][:300]}")
            if item.get("code_snippet"):
                code = str(item['code_snippet'])[:200]
                lines.append(f"- 代码: ```\n{code}\n```")
            if item.get("icon"):
                lines.append(f"- 图标: {item['icon']}")

        return "\n".join(lines)

    def _strip_markdown(self, text: str) -> str:
        """去除 markdown 代码块包装"""
        import re
        text = text.strip()
        match = re.match(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text

    async def _call_minimax(
        self,
        system_prompt: str,
        user_prompt: str,
        retry_count: int = 2,
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
                    "temperature": 0.6,
                    "max_tokens": 8192,
                }

                async with httpx.AsyncClient(timeout=45.0) as client:
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

        raise RuntimeError(f"MiniMax API failed after {retry_count} attempts. Last error: {last_error}")

    def _validate_slide(self, slide: dict, fallback_title: str, scene_id: str = "") -> dict:
        """验证和修复 slide 数据"""
        # 确保必要字段存在
        if "id" not in slide:
            slide["id"] = f"slide-{random.randint(1000, 9999)}"

        if scene_id:
            slide["scene_id"] = scene_id

        if "viewportSize" not in slide:
            slide["viewportSize"] = {"width": VIEWPORT_W, "height": VIEWPORT_H}

        if "viewportRatio" not in slide:
            slide["viewportRatio"] = VIEWPORT_H / VIEWPORT_W

        if "background" not in slide:
            slide["background"] = {"type": "solid", "color": "#0F172A"}

        if "elements" not in slide:
            slide["elements"] = []

        if "theme" not in slide:
            slide["theme"] = {
                "themeColors": ["#3B82F6", "#10B981", "#F59E0B"],
                "fontColor": "#E2E8F0",
                "backgroundColor": "#0F172A",
            }

        # 去重和修复元素（保留原始渲染顺序！）
        validated_elements = []
        seen_ids = set()

        for el in slide.get("elements", []):
            if not isinstance(el, dict) or "type" not in el:
                continue

            el_id = el.get("id", "")
            if el_id in seen_ids:
                continue
            seen_ids.add(el_id)

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

            validated_elements.append(el)

        # NOTE: 不重新排序元素！OpenMAIC 的 elements 数组顺序就是渲染顺序（z-index），
        # 按 top/left 排序会破坏背景shape和前景text的层级关系。
        slide["elements"] = validated_elements
        return slide

    def _inject_theme(self, slide: dict, design_style: str) -> dict:
        """注入统一的暗色主题配色，确保高对比度可读性。

        平台为暗色主题，强制所有幻灯片使用 dark-tech 配色，
        避免浅色背景 + 浅色文字导致的可读性问题。
        """
        theme = self.STYLE_THEMES["dark-tech"]  # 始终强制暗色主题

        # 注入 theme 字段
        slide["theme"] = {
            "themeColors": [theme["accent"], theme["success"], theme["warning"]],
            "fontColor": theme["text"],
            "backgroundColor": theme["bg"],
        }

        # 强制背景为暗色
        bg = slide.get("background", {})
        if isinstance(bg, dict):
            if bg.get("type") == "solid":
                bg["color"] = theme["bg"]
            slide["background"] = bg

        # 修复文字对比度：确保所有 text 元素使用浅色文字
        self._fix_text_contrast(slide, theme)

        return slide

    def _fix_text_contrast(self, slide: dict, theme: dict) -> None:
        """遍历所有 text/code 元素，修复颜色对比度问题。

        暗色背景上使用浅色文字，避免 LLM 输出浅色主题配色导致不可读。
        """
        import re

        bg_color = theme.get("bg", "#0F172A")
        text_color = theme.get("text", "#E2E8F0")
        text_secondary = theme.get("text_secondary", "#94A3B8")

        # 判断背景是否为深色（简单亮度计算）
        def is_dark_color(hex_color: str) -> bool:
            try:
                hex_color = hex_color.lstrip("#")
                if len(hex_color) == 3:
                    hex_color = "".join(c * 2 for c in hex_color)
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                brightness = (r * 299 + g * 587 + b * 114) / 1000
                return brightness < 128
            except Exception:
                return True  # 默认当作深色处理

        is_dark_bg = is_dark_color(bg_color)

        # 浅色文字列表（用于替换深色文字）
        light_texts = ["#E2E8F0", "#F1F5F9", "#FFFFFF", "#FFFFFF", "#CBD5E1", "#94A3B8"]
        dark_texts = ["#1E293B", "#334155", "#0F172A", "#000000", "#475569", "#64748B"]

        for el in slide.get("elements", []):
            if not isinstance(el, dict):
                continue

            el_type = el.get("type", "")
            if el_type not in ("text", "code"):
                continue

            # 修复 defaultColor
            dc = el.get("defaultColor", "")
            if dc and isinstance(dc, str):
                dc_lower = dc.lower()
                if is_dark_bg and dc_lower in dark_texts:
                    el["defaultColor"] = text_color
                elif not is_dark_bg and dc_lower in light_texts:
                    el["defaultColor"] = "#1E293B"

            # 修复 content 中的内联颜色样式
            content = el.get("content", "")
            if content and isinstance(content, str):
                # 替换深色文字颜色为浅色（暗色背景）
                for dark in dark_texts:
                    if dark.lower() in content.lower():
                        content = content.lower().replace(dark.lower(), text_color.lower())
                el["content"] = content

            # 修复 fill（文字元素不应有深色填充）
            fill = el.get("fill", "")
            if fill and isinstance(fill, str) and fill.lower() != "transparent":
                if is_dark_bg and is_dark_color(fill):
                    el["fill"] = "transparent"

    def _synthesize_actions(
        self, slide: dict, content: list, scene_id: str = ""
    ) -> list[dict]:
        """
        从幻灯片元素合成 action 序列。
        智能匹配实际存在的元素，不依赖固定的 ID 命名约定。
        """
        if not content:
            return []

        elements = slide.get("elements", [])
        actions = []

        # 收集所有可用元素按类型分组
        code_elements = [el for el in elements if el.get("type") == "code"]
        text_elements = [el for el in elements if el.get("type") == "text"]
        shape_elements = [el for el in elements if el.get("type") == "shape"]

        # 为每个内容项生成 speech + spotlight 动作
        for idx, item in enumerate(content):
            sub_title = item.get("sub_title", "")
            text = item.get("text", "")
            code_snippet = item.get("code_snippet", "")

            # 构造语音文本
            speech_parts = []
            if sub_title:
                speech_parts.append(sub_title)
            if text:
                speech_parts.append(text[:400])
            speech_text = "。".join(speech_parts) if speech_parts else ""

            if not speech_text and not code_snippet:
                continue

            # 1) speech action
            if speech_text:
                actions.append({"type": "speech", "text": speech_text})

            # 2) spotlight — 高亮对应的文本或形状元素
            # 策略：按索引匹配，或匹配内容关键字
            spotlight_target = None
            if idx < len(text_elements):
                spotlight_target = text_elements[idx].get("id")
            elif idx < len(shape_elements):
                spotlight_target = shape_elements[idx].get("id")

            if spotlight_target:
                actions.append({
                    "type": "spotlight",
                    "elementId": spotlight_target,
                    "duration": 4000,
                })

            # 3) laser — 指向代码块
            if code_snippet and str(code_snippet).strip():
                if idx < len(code_elements):
                    code_id = code_elements[idx].get("id")
                    if code_id:
                        actions.append({
                            "type": "laser",
                            "elementId": code_id,
                            "duration": 3000,
                        })

        # 兜底：如果没有生成任何 action，为第一个文本元素添加 spotlight
        if not actions and text_elements:
            actions.append({
                "type": "spotlight",
                "elementId": text_elements[0].get("id", ""),
                "duration": 3000,
            })

        return actions


# ============================================================================
# 单例
# ============================================================================

_provider = None


def get_ppt_provider() -> MiniMaxPPTProvider:
    global _provider
    if _provider is None:
        _provider = MiniMaxPPTProvider()
    return _provider
