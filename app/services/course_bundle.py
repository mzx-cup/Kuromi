# -*- coding: utf-8 -*-
"""Phase 2 — 9 件套课程包并行编排器.

职责:
  1. 接收 1 份 CourseOutline 候选 + 脑暴上下文(槽位 / 画像),并行 9 件 LLM 真生成
  2. 复用 `llm_json` 通用解析器(build_prompt + retry + Pydantic 校验)
  3. 每件独立 try/except,失败返回 fallback JSON,不阻塞整体
  4. Semaphore(6) 限并发,SSE AsyncGenerator 逐件吐 component_ready 事件

公共 context: outline_summary(标题 + 3 行摘要) 作为每件 prompt 的前置注入,
避免每件重复读完整大纲.

公开 API:
  - generate_bundle(outline, ctx) -> AsyncGenerator[dict]   (SSE 事件流)
  - generate_bundle_sync(outline, ctx) -> CourseBundle       (一次性,测试/手工用)
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Optional

from app.services.course_schemas import (
    COMPONENT_NAMES,
    AbilityGraphArtifact,
    CaseStudyArtifact,
    CourseBundle,
    ExerciseArtifact,
    KnowledgeGraphArtifact,
    LessonPlanArtifact,
    OutlineArtifact,
    PPTArtifact,
    ProjectArtifact,
    RadarArtifact,
    SurveyArtifact,
)
from app.services.llm_json import LLMJsonError, llm_json
from prompts import build_prompt
from state import LearningPortrait

logger = logging.getLogger("starlearn.course_bundle")

# 并发上限: 9 件套 + 扩展件约 10 个组件, 6 并发 2 波跑完 (原 3 并发要 4 波)
BUNDLE_CONCURRENCY = 6
# PPT 逐场景生成独立并发 (PPT 是单组件内部再开 N 个场景任务, 不占外层槽位)
PPT_SCENE_CONCURRENCY = 6


# ============================================================
# 公共 context 构造
# ============================================================

def build_outline_summary(outline: dict[str, Any]) -> dict[str, Any]:
    """从 outline 字典里抠出 9 件公共 context."""
    scenes = outline.get("scenes", []) or []
    scene_titles = [s.get("title", "") for s in scenes if isinstance(s, dict)]
    return {
        "title": outline.get("title", ""),
        "description": outline.get("description", ""),
        "total_scenes": len(scenes),
        "scene_titles": scene_titles,
        "estimated_min": sum(s.get("duration_min", 0) for s in scenes if isinstance(s, dict)),
    }


def build_bundle_context(
    outline: dict[str, Any],
    slots: dict[str, Any],
    portrait: Optional[LearningPortrait] = None,
) -> dict[str, Any]:
    """9 件 prompt 都要用到的公共 variables(每件在自己 prompt 里加)."""
    summary = build_outline_summary(outline)
    portrait_dict: dict[str, Any] = {}
    if portrait is not None:
        try:
            portrait_dict = portrait.model_dump()
        except Exception:
            portrait_dict = {}
    return {
        "course_title": summary["title"],
        "course_description": summary["description"],
        "outline_summary": summary,
        "scenes_json": json.dumps(outline.get("scenes", []), ensure_ascii=False, indent=2),
        "obg_pbl_mode": outline.get("mode", "obg"),
        "slot_goal": slots.get("goal") or "(未填, 用画像默认)",
        "slot_base": slots.get("base") or "(未填, 用画像默认)",
        "slot_path": slots.get("path") or "(未填, 用画像默认)",
        "slot_case": slots.get("case") or "(未填, 可空)",
        "learning_goals": portrait_dict.get("learning_goal", {}).get("current", "") or "(画像未提供)",
        "knowledge_base": portrait_dict.get("knowledge_mastery", {}).get("level", "") or "(画像未提供)",
        "code_skill": portrait_dict.get("code_skill", {}).get("level", "") or "(画像未提供)",
    }


# ============================================================
# 单件生成器 — 每件内部用 llm_json 拿 Pydantic 实例,失败时写 fallback
# ============================================================

def _fallback_payload(component: str, note: str) -> dict[str, Any]:
    """统一的 fallback JSON 形状(供前端降级渲染)."""
    return {
        "status": "fallback",
        "note": f"{note}; 占位生成",
        "schema_hint": {"component": component},
    }


async def _gen_outline(ctx: dict, _outline: dict[str, Any]) -> dict:
    """outline 复用上游传入(脑暴已生成),不重新跑 LLM."""
    scenes = _outline.get("scenes", [])
    total_min = sum(s.get("duration_min", 0) for s in scenes if isinstance(s, dict))
    artifact = OutlineArtifact(
        scenes=scenes,
        total_scenes=len(scenes),
        estimated_total_min=total_min,
    )
    return artifact.model_dump()


async def _gen_ppt(ctx: dict, _outline: dict[str, Any]) -> dict:
    """对每个 scene 并行生成 slides — 混合策略:
    - 80% 走 MiniMax PPT provider → OpenMAIC 格式 (elements/background/theme)
    - 其余走 LLM slide_content_v2 → 卡片格式
    **后端硬约束**: 每张幻灯片强制指定 layout + style, 覆盖 LLM/Provider 的随机选择, 保证多样性.
    **课程级主题**: 同一门课固定 1 套设计风格 (由课程标题哈希决定),
    避免整套 PPT 在 8 种风格间跳变导致配色割裂; 视觉多样性由 layout 轮换提供.
    """
    import random as _random
    scenes = _outline.get("scenes", []) or []
    if not scenes:
        logger.warning("[course_bundle] ppt 无场景, 返回空 slides")
        return PPTArtifact(slide_count=0, slide_titles=[], slides=[]).model_dump()

    all_slides: list[dict] = []
    slide_titles: list[str] = []
    sem = asyncio.Semaphore(PPT_SCENE_CONCURRENCY)
    minimax_ratio = 0.8  # 80% MiniMax (OpenMAIC 精美格式), 失败自动回退 LLM

    # 强制轮换池 — 与 minimax.STYLE_THEMES 保持同步
    DESIGN_STYLES = [
        "dark-tech", "modern", "minimal", "professional",
        "ocean-glass", "sunset-warm", "forest-green", "midnight-violet",
    ]
    # 卡片格式(slides_v2 content)前端真正注册的布局 — OpenMAIC 专属布局
    # (terminal-style/api-doc 等)对卡片渲染无意义, 会静默降级成 spotlight-focus
    CARD_LAYOUT_POOL = [
        "edu-welcome", "header-content", "two-column", "grid-cards",
        "spotlight-focus", "isometric-cards", "dark-header", "quote-wall",
        "info-graphic", "stair-step", "kinetic-type", "gradient-split",
        "circle-radial", "edu-definition", "edu-example", "edu-summary",
        "title-only",
    ]
    # OpenMAIC 元素格式幻灯片的布局池 (provider 自由设计元素)
    ELEMENT_LAYOUT_POOL = [
        "title-only", "header-content", "two-column", "code-showcase",
        "terminal-style", "concept-code", "api-doc", "step-by-step",
        "grid-cards", "comparison", "spotlight-focus", "kinetic-type",
        "isometric-cards", "orbit-ring", "gradient-split", "dark-header",
        "circle-radial", "stair-step", "quote-wall", "info-graphic",
    ]
    STYLE_TO_COLOR = {
        "dark-tech": "blue", "modern": "yellow", "minimal": "green",
        "professional": "purple", "ocean-glass": "cyan", "sunset-warm": "orange",
        "forest-green": "green", "midnight-violet": "purple",
    }

    # 课程级基础风格: 课程标题哈希 → 稳定选择, 重生成不漂移
    _course_key = f"{ctx.get('course_title', '')}|{len(scenes)}"
    _base_style = DESIGN_STYLES[sum(ord(c) for c in _course_key) % len(DESIGN_STYLES)]
    logger.info(f"[course_bundle] ppt 课程级主题: {_base_style}")

    def _pick_style_for_index(idx: int, total: int) -> str:
        """整套课程统一风格 (视觉连贯), 不再逐页轮换"""
        return _base_style

    def _pick_layout_for_index(idx: int, total: int, pool: list[str] | None = None) -> str:
        """均匀分布布局, 用质数步长"""
        p = pool or CARD_LAYOUT_POOL
        return p[(idx * 11) % len(p)]

    # ---- MiniMax 路径 ----
    async def _minimax_slide(scene: dict, idx: int) -> tuple[int, list[dict]]:
        async with sem:
            scene_title = scene.get("title", "")
            scene_desc = scene.get("description", "")
            key_points = scene.get("key_points", [])
            forced_style = _pick_style_for_index(idx, len(scenes))
            forced_layout = _pick_layout_for_index(idx, len(scenes), ELEMENT_LAYOUT_POOL)
            forced_color = STYLE_TO_COLOR.get(forced_style, "blue")
            try:
                from app.services.ppt.minimax import STYLE_THEMES as _MM_THEMES, get_ppt_provider
                from app.services.ppt.types import PPTGenerationRequest
                provider = get_ppt_provider()
                # 从 key_points 构造 content items
                content_items = []
                if scene_desc:
                    content_items.append({"sub_title": "", "text": scene_desc})
                for kp in key_points[:5]:
                    content_items.append({"sub_title": "", "text": kp})
                req = PPTGenerationRequest(
                    course_title=_outline.get("title", ctx["course_title"]),
                    scene_title=scene_title,
                    scene_id=str(idx),
                    scene_type="slide",
                    content=content_items,
                    design_style=forced_style,
                    layout_hint=forced_layout,
                )
                result = await provider.generate(req)
                if result.success and result.slide:
                    slide = result.slide
                    # **硬约束覆盖**: 即便 provider 返回不同 layout, 也强制替换
                    slide["layoutType"] = forced_layout
                    slide["layout_type"] = forced_layout
                    # theme 必须是 dict (SlideV2.theme: Optional[dict]), 不能是字符串
                    # primary 用该风格真实 accent 色, 而非硬编码蓝
                    mm_theme = _MM_THEMES.get(forced_style, {})
                    slide["theme"] = {
                        "name": forced_style,
                        "primary": mm_theme.get("accent", "#1E40AF"),
                        "background": mm_theme.get("bg", "#0F172A"),
                    }
                    slide["_theme"] = forced_style
                    slide["_color_hint"] = forced_color
                    slide["_scene_title"] = scene_title
                    slide["_via"] = "minimax"
                    return idx, [slide]
                else:
                    logger.warning(f"[course_bundle] MiniMax ppt scene '{scene_title}' 失败: {result.error}, 回退 LLM")
                    return await _llm_slide(scene, idx, forced_style, forced_layout, forced_color)
            except Exception as e:
                logger.warning(f"[course_bundle] MiniMax ppt scene '{scene_title}' 异常: {e}, 回退 LLM")
                return await _llm_slide(scene, idx, forced_style, forced_layout, forced_color)

    # ---- LLM 路径 ----
    from pydantic import BaseModel, Field as PydField

    class _SlideContent(BaseModel):
        subTitle: str = ""
        bullets: list[str] = PydField(default_factory=list)
        narration: str = ""
        icon: str = "book"
        colorTheme: str = "blue"
        codeSnippet: str = ""
        image_prompt: str = ""

    class _Slide(BaseModel):
        layoutType: str = "two-column"
        title: str = ""
        content: list[_SlideContent] = PydField(default_factory=list)
        teacherActions: list[dict] = PydField(default_factory=list)

    class _SceneSlides(BaseModel):
        slides: list[_Slide] = PydField(default_factory=list)

    async def _llm_slide(
        scene: dict, idx: int,
        forced_style: str | None = None,
        forced_layout: str | None = None,
        forced_color: str | None = None,
    ) -> tuple[int, list[dict]]:
        async with sem:
            scene_title = scene.get("title", "")
            scene_desc = scene.get("description", "")
            key_points = scene.get("key_points", [])
            scene_type = scene.get("type", "slide")
            prev_title = scenes[idx - 1].get("title", "") if idx > 0 else ""
            next_title = scenes[idx + 1].get("title", "") if idx + 1 < len(scenes) else ""

            # 若上层没传 (直接 LLM 路径), 自行强制
            if forced_style is None:
                forced_style = _pick_style_for_index(idx, len(scenes))
            if forced_layout is None:
                forced_layout = _pick_layout_for_index(idx, len(scenes))
            if forced_color is None:
                forced_color = STYLE_TO_COLOR.get(forced_style, "blue")

            variables: dict[str, Any] = {
                "course_title": _outline.get("title", ctx["course_title"]),
                "scene_type": scene_type,
                "outline_title": scene_title,
                "outline_description": scene_desc,
                "key_points": ", ".join(key_points) if key_points else "(无)",
                "prev_outline_title": prev_title or "(无, 本场景为首节)",
                "next_outline_title": next_title or "(无, 本场景为末节)",
                "pdf_text": "",
                "web_search_context": "",
                "available_layouts": ", ".join(CARD_LAYOUT_POOL),
                "_hint_color": forced_color,
                "_hint_layout": forced_layout,
                "_hint_style": forced_style,
            }
            try:
                instance = await llm_json("slide_content_v2", variables, _SceneSlides, temperature=0.55, max_retries=2)
                slides = instance.model_dump().get("slides", []) or []
            except LLMJsonError as e:
                logger.warning(f"[course_bundle] ppt LLM scene '{scene_title}' 失败, 走兜底: {e}")
                slides = _fallback_slides_for_scene(scene_title, scene_desc, key_points, forced_layout, forced_color)

            # **硬约束覆盖**: 不论 LLM 选什么, 后端强制 layout + color
            for s in slides:
                s["layoutType"] = forced_layout
                s["layout_type"] = forced_layout
                # 覆盖所有 content[].colorTheme
                for c in s.get("content", []) or []:
                    if isinstance(c, dict):
                        c["colorTheme"] = forced_color
                s.setdefault("_scene_title", scene_title)
                s["_via"] = "llm"
                s["_theme"] = forced_style
                s["_color_hint"] = forced_color
            return idx, slides

    # ---- 调度: 60% MiniMax, 40% LLM ----
    tasks = []
    for i, s in enumerate(scenes):
        if not isinstance(s, dict):
            continue
        use_minimax = _random.random() < minimax_ratio
        tasks.append(_minimax_slide(s, i) if use_minimax else _llm_slide(s, i))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for raw in results:
        if isinstance(raw, Exception):
            logger.warning(f"[course_bundle] ppt task exception: {raw}")
            continue
        _idx, slides = raw
        all_slides.extend(slides)
        for s in slides:
            title = s.get("title", "")
            if title:
                slide_titles.append(title)

    if not all_slides:
        for idx_fb, scene in enumerate(scenes):
            if isinstance(scene, dict):
                fb_style = _pick_style_for_index(idx_fb, len(scenes))
                fb_layout = _pick_layout_for_index(idx_fb, len(scenes))
                fb_color = STYLE_TO_COLOR.get(fb_style, "blue")
                fallback = _fallback_slides_for_scene(
                    scene.get("title", ""), scene.get("description", ""), scene.get("key_points", []),
                    fb_layout, fb_color,
                )
                all_slides.extend(fallback)

    return PPTArtifact(
        slide_count=len(all_slides),
        slide_titles=slide_titles,
        slides=all_slides,
    ).model_dump()


def _fallback_slides_for_scene(
    title: str, description: str, key_points: list,
    forced_layout: str = "edu-keypoints", forced_color: str = "blue",
) -> list[dict]:
    """LLM 全挂时的 PPT 兜底页. 接受强制 layout/color 以保持多样性."""
    key_items = [f"<li>{p}</li>" for p in (key_points or [])[:4]]
    html = f"<h2>{title or '章节'}</h2><p>{description or '本节内容'}</p><ul>{''.join(key_items)}</ul>"
    return [{
        "layoutType": forced_layout,
        "layout_type": forced_layout,
        "title": title or "章节",
        "content": [{
            "subTitle": title or "章节",
            "bullets": (key_points or ["核心概念"])[:4],
            "narration": f"本节我们来学习{title or '新内容'}。{description or ''}",
            "icon": "book",
            "colorTheme": forced_color,
        }],
        "teacherActions": [],
        "_scene_title": title,
        "_color_hint": forced_color,
    }]


async def _gen_plan(ctx: dict, _outline: dict[str, Any]) -> dict:
    variables = {
        "course_title": ctx["course_title"],
        "obg_pbl_mode": ctx["obg_pbl_mode"],
        "scenes_json": ctx["scenes_json"],
    }
    try:
        instance = await llm_json("lesson_plan", variables, LessonPlanArtifact)
        return instance.model_dump()
    except LLMJsonError as e:
        logger.warning(f"[course_bundle] plan fallback: {e}")
        return _fallback_payload("plan", str(e))


async def _gen_graph(ctx: dict, _outline: dict[str, Any]) -> dict:
    variables = {
        "course_title": ctx["course_title"],
        "scenes_json": ctx["scenes_json"],
    }
    try:
        instance = await llm_json("knowledge_graph", variables, KnowledgeGraphArtifact)
        return instance.model_dump()
    except LLMJsonError as e:
        logger.warning(f"[course_bundle] graph fallback: {e}")
        return _fallback_payload("graph", str(e))


async def _gen_ability_graph(ctx: dict, _outline: dict[str, Any]) -> dict:
    """缺口1:能力图谱生成(不进 COMPONENT_NAMES,仅挂载在 dispatcher 中)。

    复用脑暴槽位 slot_goal 和画像 learning_goals,让 LLM 输出更对齐用户需求。
    自动从 competencies + edges 衍生 graph_view,供前端 graph 组件直接渲染。
    """
    variables = {
        "course_title": ctx["course_title"],
        "scenes_json": ctx["scenes_json"],
        "obg_pbl_mode": ctx["obg_pbl_mode"],
        "slot_goal": ctx.get("slot_goal", "") or "(未填)",
        "learning_goals": ctx.get("learning_goals", "") or "(画像未提供)",
    }
    try:
        instance = await llm_json("ability_graph", variables, AbilityGraphArtifact)
        d = instance.model_dump()
        # 自动衍生 graph_view(同 KnowledgeGraph 形状)
        d["graph_view"] = {
            "nodes": [
                {"id": c["id"], "label": c["name"], "layer": c.get("bloom_level", 1)}
                for c in d.get("competencies", []) if isinstance(c, dict)
            ],
            "edges": [
                {"from": e.get("from_id", e.get("from")),
                 "to":   e.get("to_id",   e.get("to")),
                 "label": e.get("relation", "")}
                for e in d.get("edges", []) if isinstance(e, dict)
            ],
        }
        d["status"] = "ok"
        return d
    except LLMJsonError as e:
        logger.warning(f"[course_bundle] ability_graph fallback: {e}")
        return _fallback_payload("ability_graph", str(e))


async def _gen_radar(ctx: dict, _outline: dict[str, Any], portrait: Optional[LearningPortrait]) -> dict:
    """雷达 = 画像聚合 + LLM 估"完成本课程后预期"."""
    pre = _aggregate_radar(portrait)
    variables = {
        "course_title": ctx["course_title"],
        "obg_pbl_mode": ctx["obg_pbl_mode"],
        "learning_goals": ctx["learning_goals"],
        "knowledge_base": ctx["knowledge_base"],
    }
    try:
        instance = await llm_json("radar_init", variables, RadarArtifact)
        d = instance.model_dump()
        d["status"] = "ok"
        d["pre_course"] = pre
        return d
    except LLMJsonError as e:
        logger.warning(f"[course_bundle] radar fallback: {e}")
        fb = _fallback_payload("radar", str(e))
        fb["pre_course"] = pre
        return fb


def _aggregate_radar(portrait: Optional[LearningPortrait]) -> dict[str, float]:
    """复用 portrait_aggregator;画像缺失时给 0."""
    if portrait is None:
        return {k: 0.0 for k in (
            "knowledge_mastery", "code_skill", "cognitive_level",
            "learning_goal", "weakness", "focus_level",
        )}
    try:
        from app.services.portrait_aggregator import aggregate_portrait_snapshot
        snap = aggregate_portrait_snapshot(portrait, telemetry=None)
        return snap.get("radar", {})
    except Exception as e:
        logger.warning(f"[course_bundle] aggregate_radar failed: {e}")
        return {}


async def _gen_project(ctx: dict, _outline: dict[str, Any]) -> dict:
    variables = {
        "course_title": ctx["course_title"],
        "obg_pbl_mode": ctx["obg_pbl_mode"],
        "scenes_json": ctx["scenes_json"],
    }
    try:
        instance = await llm_json("project_brief", variables, ProjectArtifact)
        return instance.model_dump()
    except LLMJsonError as e:
        logger.warning(f"[course_bundle] project fallback: {e}")
        return _fallback_payload("project", str(e))


async def _gen_case(ctx: dict, _outline: dict[str, Any]) -> dict:
    variables = {
        "course_title": ctx["course_title"],
        "scenes_json": ctx["scenes_json"],
    }
    try:
        instance = await llm_json("case_study", variables, CaseStudyArtifact)
        return instance.model_dump()
    except LLMJsonError as e:
        logger.warning(f"[course_bundle] case fallback: {e}")
        return _fallback_payload("case", str(e))


async def _gen_exercises(ctx: dict, _outline: dict[str, Any]) -> dict:
    """对每个 scene 各出一份习题,合并到 1 个 ExerciseArtifact."""
    scenes = _outline.get("scenes", [])
    all_questions: list[dict] = []
    by_scene: dict[str, list[int]] = {}
    next_id = 1

    sem = asyncio.Semaphore(BUNDLE_CONCURRENCY)

    async def _one(scene: dict) -> list[dict]:
        async with sem:
            scene_id = scene.get("id", "")
            variables = {
                "course_title": ctx["course_title"],
                "scene_id": scene_id,
                "scene_title": scene.get("title", ""),
                "scene_description": scene.get("description", ""),
                "key_points": ", ".join(scene.get("key_points", []) or []),
                "difficulty": "medium",
            }
            try:
                art = await llm_json("exercises", variables, ExerciseArtifact)
                return [(q.model_dump(), scene_id) for q in art.questions]
            except LLMJsonError as e:
                logger.warning(f"[course_bundle] exercises scene {scene_id} fallback: {e}")
                return []

    tasks = [_one(s) for s in scenes if isinstance(s, dict)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for raw in results:
        if isinstance(raw, Exception):
            logger.warning(f"[course_bundle] exercises task exception: {raw}")
            continue
        for q_dump, scene_id in raw:
            q_dump["id"] = next_id
            all_questions.append(q_dump)
            by_scene.setdefault(scene_id, []).append(next_id)
            next_id += 1

    if not all_questions:
        return _fallback_payload("exercises", "所有场景习题均未生成")

    return ExerciseArtifact(
        questions=all_questions,
        by_scene=by_scene,
    ).model_dump()


async def _gen_survey(ctx: dict, _outline: dict[str, Any]) -> dict:
    variables = {
        "course_title": ctx["course_title"],
        "learning_goals": ctx["learning_goals"],
        "estimated_min": ctx["outline_summary"].get("estimated_min", 30),
    }
    try:
        instance = await llm_json("survey", variables, SurveyArtifact)
        return instance.model_dump()
    except LLMJsonError as e:
        logger.warning(f"[course_bundle] survey fallback: {e}")
        return _fallback_payload("survey", str(e))


# ============================================================
# 注册表
# ============================================================

def _component_dispatcher(
    ctx: dict,
    outline: dict[str, Any],
    portrait: Optional[LearningPortrait],
):
    """每件 → 协程工厂;调用方 await."""
    return {
        "outline":   lambda: _gen_outline(ctx, outline),
        "plan":      lambda: _gen_plan(ctx, outline),
        "ppt":       lambda: _gen_ppt(ctx, outline),
        "graph":     lambda: _gen_graph(ctx, outline),
        "ability_graph": lambda: _gen_ability_graph(ctx, outline),  # 缺口1:并行扩展,不入 COMPONENT_NAMES
        "radar":     lambda: _gen_radar(ctx, outline, portrait),
        "project":   lambda: _gen_project(ctx, outline),
        "case":      lambda: _gen_case(ctx, outline),
        "exercises": lambda: _gen_exercises(ctx, outline),
        "survey":    lambda: _gen_survey(ctx, outline),
    }


async def _run_one_component(
    name: str,
    coro_factory,
    sem: asyncio.Semaphore,
    audit_agent: Optional[Any] = None,
    max_retries: int = 2,
) -> tuple[str, dict]:
    """跑 1 件,返回 (name, payload). 任何异常 → fallback.

    缺口5:加 audit_agent 参数 → 生成后过 AuditAgent;
    risk=high 时自动重生成,最多 max_retries 轮。
    """
    async with sem:
        last_err: Optional[str] = None
        for attempt in range(max_retries + 1):
            try:
                payload = await coro_factory()
            except Exception as e:
                logger.warning(f"[course_bundle] {name} attempt {attempt+1} 异常: {e}")
                last_err = str(e)
                payload = _fallback_payload(name, last_err)

            # 审核(仅 status=ok 时检查)
            if payload.get("status") == "ok" and audit_agent is not None:
                try:
                    import json as _json
                    text = _json.dumps(payload, ensure_ascii=False)[:2000]
                    result = await audit_agent.run(
                        user_id="course-bundle",
                        input_text="",
                        output_text=text,
                    )
                    if getattr(result, "risk_level", None) == "high":
                        logger.info(
                            f"[course_bundle] {name} attempt {attempt+1} 被拒: "
                            f"{getattr(result, 'reason', '?')}"
                        )
                        if attempt < max_retries:
                            continue  # 重试
                        payload["audit_rejected"] = True
                        payload["audit_reason"] = getattr(result, "reason", "unknown")
                    else:
                        payload["audit_risk"] = getattr(result, "risk_level", "low")
                        payload["audit_jailbreak_score"] = getattr(result, "jailbreak_score", 0.0)
                except Exception as audit_err:
                    # 审核失败不应阻塞主流程,记录告警
                    logger.warning(f"[course_bundle] {name} audit 异常(忽略): {audit_err}")
            return name, payload

        # 全部重试仍失败
        payload["status"] = "fallback"
        payload["audit_rejected"] = True
        payload["audit_reason"] = f"经 {max_retries+1} 轮仍被拒: {last_err or 'unknown'}"
        return name, payload


def _get_audit_agent() -> Optional[Any]:
    """懒加载 AuditAgent(避免 import 期循环依赖)."""
    try:
        from app.agents.audit import AuditAgent
        return AuditAgent()
    except Exception as e:
        logger.warning(f"[course_bundle] AuditAgent 加载失败: {e}; 关闭审核循环")
        return None


# ============================================================
# 公开 API — 一次性
# ============================================================

async def generate_bundle_sync(
    outline: dict[str, Any],
    slots: dict[str, Any],
    portrait: Optional[LearningPortrait] = None,
    enabled_components: Optional[list[str]] = None,
) -> CourseBundle:
    """9 件一次性跑完,返回 CourseBundle(测试/手工用).

    缺口1:缺省时跑 COMPONENT_NAMES(9 件) + dispatcher 中并行扩展的额外件(如 ability_graph)。
    """
    ctx = build_bundle_context(outline, slots, portrait)
    factories = _component_dispatcher(ctx, outline, portrait)
    if enabled_components is None or len(enabled_components) == 0:
        # 9 件套 + dispatcher 中所有额外件(如 ability_graph)
        names = list(COMPONENT_NAMES) + [
            k for k in factories if k not in COMPONENT_NAMES
        ]
    else:
        names = [n for n in enabled_components if n in factories]
    sem = asyncio.Semaphore(BUNDLE_CONCURRENCY)

    tasks = [
        _run_one_component(n, factories[n], sem, audit_agent=_get_audit_agent())
        for n in names if n in factories
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    components: dict[str, dict] = {}
    for raw in results:
        if isinstance(raw, Exception):
            logger.warning(f"[course_bundle] top-level task exception: {raw}")
            continue
        name, payload = raw
        components[name] = payload

    return CourseBundle(
        components=components,
        obg_pbl_mode=outline.get("mode", "obg"),
        obg_pbl_rationale=outline.get("rationale", ""),
        outline_summary=build_outline_summary(outline),
        brainstorm={"slots": slots, "mode": outline.get("mode", "obg")},
    )


# ============================================================
# 公开 API — SSE 流式(每件 ready 即吐 1 个 component_ready 事件)
# ============================================================

async def generate_bundle(
    outline: dict[str, Any],
    slots: dict[str, Any],
    portrait: Optional[LearningPortrait] = None,
    enabled_components: Optional[list[str]] = None,
) -> AsyncGenerator[dict, None]:
    """9 件 SSE 事件流,每件完成吐 1 个 component_ready:{name}.

    缺口1:缺省时跑 COMPONENT_NAMES(9 件) + dispatcher 中并行扩展的额外件(如 ability_graph)。
    缺口5:每件生成后过 AuditAgent 审核,risk=high 自动重试;产生 component_retry 事件。

    Yields:
        {"type": "component_start", "name": ...}      # 开始
        {"type": "component_retry", "name": ..., "reason": ..., "attempts": N}  # 审核重试
        {"type": "component_ready", "name": ..., "payload": ...}  # 完成
        {"type": "bundle_complete", "bundle": CourseBundle.model_dump()}  # 全部完成
    """
    ctx = build_bundle_context(outline, slots, portrait)
    factories = _component_dispatcher(ctx, outline, portrait)
    if enabled_components is None or len(enabled_components) == 0:
        # 9 件套 + dispatcher 中所有额外件
        names = list(COMPONENT_NAMES) + [
            k for k in factories if k not in COMPONENT_NAMES
        ]
    else:
        names = [n for n in enabled_components if n in factories]
    sem = asyncio.Semaphore(BUNDLE_CONCURRENCY)
    audit_agent = _get_audit_agent()

    # 启动所有任务,但 await 时逐件让出
    tasks: dict[str, asyncio.Task] = {}
    for n in names:
        yield {"type": "component_start", "name": n}
        tasks[n] = asyncio.create_task(
            _run_one_component(n, factories[n], sem, audit_agent=audit_agent)
        )

    components: dict[str, dict] = {}
    # asyncio.as_completed 让第一件完成即让出
    pending = set(tasks.values())
    name_by_task = {t: n for n, t in tasks.items()}
    for fut in asyncio.as_completed(pending):
        raw = await fut
        if isinstance(raw, Exception):
            logger.warning(f"[course_bundle] streamed task exception: {raw}")
            continue
        name, payload = raw
        components[name] = payload
        # 缺口5:若 audit_rejected,先吐 component_retry 事件,前端 toast 提示
        if payload.get("audit_rejected"):
            yield {
                "type": "component_retry",
                "name": name,
                "reason": payload.get("audit_reason", ""),
                "attempts": payload.get("audit_attempts", 2),
                "payload": payload,
            }
        yield {
            "type": "component_ready",
            "name": name,
            "payload": payload,
        }

    bundle = CourseBundle(
        components=components,
        obg_pbl_mode=outline.get("mode", "obg"),
        obg_pbl_rationale=outline.get("rationale", ""),
        outline_summary=build_outline_summary(outline),
        brainstorm={"slots": slots, "mode": outline.get("mode", "obg")},
    )
    yield {
        "type": "bundle_complete",
        "bundle": bundle.model_dump(),
    }
