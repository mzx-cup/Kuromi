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

## 元素 ID 命名规范（CRITICAL — 下游解析依赖）
内容元素必须按卡片分组命名，格式为 `card-{N}-*`（N 从 1 开始递增）：
- 卡片背景 shape: `"id": "card-1-bg"`
- 卡片标题 text: `"id": "card-1-title"`
- 卡片正文 text: `"id": "card-1-content"`
- 卡片内代码块: `"id": "card-1-code"`
- 卡片内图片: `"id": "card-1-image"`
页面级装饰元素（背景、分隔线）可用 `bg-*` / `deco-*` 前缀。

## 输出要求
1. 只输出JSON格式的幻灯片数据，不要任何解释
2. 每个元素必须有唯一的ID，且遵循上述 card-N 命名规范
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

    # 编程教学专用布局（20种：含 10 编程 + 5 创意 + 5 教育）
    LAYOUT_TYPES = [
        "title-only",         # 标题页
        "header-content",     # 标题+内容卡片
        "two-column",         # 两栏对比
        "code-showcase",      # 代码展示（左文右码）
        "terminal-style",     # 终端风格
        "concept-code",       # 概念+代码对照
        "api-doc",            # API文档
        "step-by-step",       # 步骤教学
        "grid-cards",         # 卡片网格
        "comparison",         # 正反对比
        # —— 新增 10 种创意/教育布局 ——
        "spotlight-focus",    # 大标题居中 + 副标题
        "kinetic-type",       # 倾斜大标题 + 装饰
        "isometric-cards",    # 卡片 3D 阴影
        "orbit-ring",         # 中央圆环 + 文字围绕
        "gradient-split",     # 左右渐变分割
        "dark-header",        # 黑色 header bar
        "circle-radial",      # 中心大圆 + 6 个小圆
        "stair-step",         # 阶梯式排列
        "quote-wall",         # 大引号 + 引用文本
        "info-graphic",       # 大数字 + 描述
        "edu-welcome",        # 大标题 + 课程名
        "edu-definition",     # 术语 + 解释
        "edu-example",        # 例题 + 解答
        "edu-summary",        # 章节小结
    ]

    # 编程场景布局选择映射（保留向后兼容）
    LAYOUT_BY_CONTENT = {
        "code": ["code-showcase", "concept-code", "terminal-style", "kinetic-type"],
        "command": ["terminal-style", "code-showcase", "dark-header"],
        "function": ["api-doc", "code-showcase", "concept-code", "info-graphic"],
        "class": ["api-doc", "concept-code", "isometric-cards"],
        "step": ["step-by-step", "grid-cards", "stair-step", "circle-radial"],
        "compare": ["comparison", "two-column", "gradient-split"],
        "overview": ["header-content", "grid-cards", "orbit-ring"],
        "intro": ["title-only", "header-content", "spotlight-focus", "edu-welcome"],
        "definition": ["concept-code", "info-graphic", "edu-definition"],
        "summary": ["quote-wall", "edu-summary", "info-graphic"],
    }

    # 编程风格定义（8 种：4 旧 + 4 新，结构化不同）
    DESIGN_STYLES = [
        "dark-tech",        # 深色科技（适合代码）
        "modern",           # 现代简约
        "minimal",          # 极简留白
        "professional",     # 专业商务
        "ocean-glass",      # 玻璃态 + 青蓝（新）
        "sunset-warm",      # 暖橙渐变（新）
        "forest-green",     # 自然绿 + 衬线（新）
        "midnight-violet",  # 深夜紫 + 大圆角（新）
    ]

    # 风格配色（每种带 gradient/font_family/card_radius/pattern 结构化差异）
    STYLE_THEMES = {
        "dark-tech": {
            "bg": "#0F172A", "card": "#1E293B", "code_bg": "#0D1117",
            "text": "#E2E8F0", "text_secondary": "#94A3B8",
            "accent": "#3B82F6", "success": "#10B981",
            "warning": "#F59E0B", "error": "#EF4444",
            "gradient": "linear-gradient(135deg, #0F172A 0%, #1E293B 100%)",
            "font_family": "mono",
            "card_radius": "md",
            "pattern": "grid",
        },
        "modern": {
            "bg": "#F8FAFC", "card": "#FFFFFF", "code_bg": "#1E293B",
            "text": "#1E293B", "text_secondary": "#64748B",
            "accent": "#3B82F6", "success": "#10B981",
            "warning": "#F59E0B", "error": "#EF4444",
            "gradient": "linear-gradient(135deg, #F8FAFC 0%, #E2E8F0 100%)",
            "font_family": "sans",
            "card_radius": "lg",
            "pattern": "none",
        },
        "minimal": {
            "bg": "#FFFFFF", "card": "#F8FAFC", "code_bg": "#0F172A",
            "text": "#0F172A", "text_secondary": "#64748B",
            "accent": "#0EA5E9", "success": "#22C55E",
            "warning": "#EAB308", "error": "#DC2626",
            "gradient": "linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%)",
            "font_family": "sans",
            "card_radius": "sm",
            "pattern": "none",
        },
        "professional": {
            "bg": "#F1F5F9", "card": "#FFFFFF", "code_bg": "#1E293B",
            "text": "#334155", "text_secondary": "#64748B",
            "accent": "#6366F1", "success": "#10B981",
            "warning": "#F59E0B", "error": "#EF4444",
            "gradient": "linear-gradient(135deg, #F1F5F9 0%, #E0E7FF 100%)",
            "font_family": "sans",
            "card_radius": "md",
            "pattern": "dots",
        },
        "ocean-glass": {
            "bg": "#E0F2FE", "card": "#FFFFFF", "code_bg": "#0C4A6E",
            "text": "#0C4A6E", "text_secondary": "#0369A1",
            "accent": "#06B6D4", "success": "#14B8A6",
            "warning": "#F59E0B", "error": "#F43F5E",
            "gradient": "linear-gradient(135deg, #E0F2FE 0%, #CFFAFE 50%, #A5F3FC 100%)",
            "font_family": "sans",
            "card_radius": "xl",
            "pattern": "waves",
        },
        "sunset-warm": {
            "bg": "#FFF7ED", "card": "#FFFFFF", "code_bg": "#7C2D12",
            "text": "#7C2D12", "text_secondary": "#9A3412",
            "accent": "#F97316", "success": "#84CC16",
            "warning": "#F59E0B", "error": "#DC2626",
            "gradient": "linear-gradient(135deg, #FED7AA 0%, #FDBA74 50%, #FB923C 100%)",
            "font_family": "rounded",
            "card_radius": "lg",
            "pattern": "none",
        },
        "forest-green": {
            "bg": "#F0FDF4", "card": "#FFFFFF", "code_bg": "#14532D",
            "text": "#14532D", "text_secondary": "#166534",
            "accent": "#16A34A", "success": "#22C55E",
            "warning": "#EAB308", "error": "#DC2626",
            "gradient": "linear-gradient(135deg, #DCFCE7 0%, #BBF7D0 100%)",
            "font_family": "serif",
            "card_radius": "md",
            "pattern": "none",
        },
        "midnight-violet": {
            "bg": "#1E1B4B", "card": "#312E81", "code_bg": "#0F0E2E",
            "text": "#E0E7FF", "text_secondary": "#A5B4FC",
            "accent": "#A78BFA", "success": "#34D399",
            "warning": "#FBBF24", "error": "#F87171",
            "gradient": "linear-gradient(135deg, #1E1B4B 0%, #4C1D95 50%, #312E81 100%)",
            "font_family": "rounded",
            "card_radius": "xl",
            "pattern": "dots",
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
            layout_type = self._select_layout(
                request.content, request.scene_type, forced_layout=request.layout_hint
            )
            design_style = self._select_design_style(
                request.content, forced_style=request.design_style
            )

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

    def _select_design_style(
        self,
        content: list,
        forced_style: str | None = None,
    ) -> str:
        """根据内容/外部指定选择设计风格

        Args:
            content: 内容列表
            forced_style: 外部强制指定的风格名（在 STYLE_THEMES 中）。若指定则直接采用。
        """
        # 优先级 1: 外部强制风格（后端硬约束）
        if forced_style and forced_style in self.STYLE_THEMES:
            self._style_history.append(forced_style)
            return forced_style

        # 优先级 2: 真正随机选择（不再有 has_code 降级）
        all_styles = list(self.STYLE_THEMES.keys())
        chosen = random.choice(all_styles)
        self._style_history.append(chosen)
        return chosen

    def _select_layout(
        self,
        content: list,
        scene_type: str,
        forced_layout: str | None = None,
    ) -> str:
        """智能选择布局：优先采用外部 hint，否则按内容特征匹配

        Args:
            content: 内容列表
            scene_type: 场景类型
            forced_layout: 外部强制指定的布局名（在 LAYOUT_TYPES 中）
        """
        if scene_type == "quiz":
            return "grid-cards"

        # 优先级 1: 外部强制布局
        if forced_layout and forced_layout in self.LAYOUT_TYPES:
            self._layout_history.append(forced_layout)
            return forced_layout

        # 优先级 2: 内容特征匹配
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
            # 默认池（更丰富）
            default_pool = [
                "header-content", "grid-cards", "two-column", "title-only",
                "spotlight-focus", "kinetic-type", "stair-step", "circle-radial",
            ]
            unused_default = [c for c in default_pool if c not in self._layout_history]
            choice = random.choice(unused_default) if unused_default else random.choice(default_pool)

        self._layout_history.append(choice)
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
        """调用 MiniMax API，带重试机制.

        复用模块级 AsyncClient (连接池 + TLS 会话复用),
        避免逐 slide 新建客户端的握手开销 (9 件套 PPT 一次生成 ~10 个场景并发调用).
        """
        last_error = None

        for attempt in range(retry_count):
            try:
                client = _get_shared_client()
                url = f"{settings.minimax_api_url}/chat/completions"
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
        """注入主题配色，确保高对比度可读性。"""
        style = design_style if design_style in self.STYLE_THEMES else "dark-tech"
        theme = self.STYLE_THEMES[style]

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
# 共享 AsyncClient: 连接池复用, 逐 slide 调用省去 TLS 握手 (~100-300ms/次)
_shared_client: httpx.AsyncClient | None = None


def _get_shared_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=45.0, write=10.0, pool=10.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _shared_client


async def close_shared_client() -> None:
    """应用关停时释放连接池(测试用; 常驻进程可不调)."""
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        await _shared_client.aclose()
    _shared_client = None


def get_ppt_provider() -> MiniMaxPPTProvider:
    global _provider
    if _provider is None:
        _provider = MiniMaxPPTProvider()
    return _provider
