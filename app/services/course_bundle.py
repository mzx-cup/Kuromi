# -*- coding: utf-8 -*-
"""Phase 2 — 9 件套课程包并行编排器.

职责:
  1. 接收 1 份 CourseOutline 候选 + 脑暴上下文(槽位 / 画像),并行 9 件 LLM 真生成
  2. 复用 `llm_json` 通用解析器(build_prompt + retry + Pydantic 校验)
  3. 每件独立 try/except,失败返回 fallback JSON,不阻塞整体
  4. Semaphore(3) 限并发,SSE AsyncGenerator 逐件吐 component_ready 事件

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

# 并发上限: 与 libs/course.py:333 对齐
BUNDLE_CONCURRENCY = 3


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
    """对每个 scene 调用 LLM 生成 2-3 页 slide_v2 幻灯片, 合并进 PPTArtifact.slides."""
    scenes = _outline.get("scenes", []) or []
    if not scenes:
        logger.warning("[course_bundle] ppt 无场景, 返回空 slides")
        return PPTArtifact(slide_count=0, slide_titles=[], slides=[]).model_dump()

    all_slides: list[dict] = []
    slide_titles: list[str] = []
    sem = asyncio.Semaphore(BUNDLE_CONCURRENCY)

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
        layoutType: str = "edu-keypoints"
        title: str = ""
        content: list[_SlideContent] = PydField(default_factory=list)
        teacherActions: list[dict] = PydField(default_factory=list)

    class _SceneSlides(BaseModel):
        slides: list[_Slide] = PydField(default_factory=list)

    async def _one_scene(scene: dict, idx: int) -> tuple[int, list[dict]]:
        async with sem:
            scene_title = scene.get("title", "")
            scene_desc = scene.get("description", "")
            key_points = scene.get("key_points", [])
            scene_type = scene.get("type", "slide")
            prev_title = scenes[idx - 1].get("title", "") if idx > 0 else ""
            next_title = scenes[idx + 1].get("title", "") if idx + 1 < len(scenes) else ""

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
                "available_layouts": "edu-welcome, edu-definition, edu-keypoints, edu-example, edu-summary, edu-programming-concept, title-only, hero-center, header-content, two-column, grid-cards, numbered-list, chapter-divider",
            }
            try:
                instance = await llm_json("slide_content_v2", variables, _SceneSlides, temperature=0.55, max_retries=2)
                slides = instance.model_dump().get("slides", []) or []
            except LLMJsonError as e:
                logger.warning(f"[course_bundle] ppt scene '{scene_title}' LLM 失败, 走兜底: {e}")
                slides = _fallback_slides_for_scene(scene_title, scene_desc, key_points)

            for s in slides:
                s.setdefault("_scene_title", scene_title)
            return idx, slides

    tasks = [_one_scene(s, i) for i, s in enumerate(scenes) if isinstance(s, dict)]
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
        # 最后兜底: 给每个 scene 至少 1 页
        for scene in scenes:
            if isinstance(scene, dict):
                fallback = _fallback_slides_for_scene(
                    scene.get("title", ""), scene.get("description", ""), scene.get("key_points", [])
                )
                all_slides.extend(fallback)

    return PPTArtifact(
        slide_count=len(all_slides),
        slide_titles=slide_titles,
        slides=all_slides,
    ).model_dump()


def _fallback_slides_for_scene(title: str, description: str, key_points: list) -> list[dict]:
    """LLM 全挂时的 PPT 兜底页."""
    key_items = [f"<li>{p}</li>" for p in (key_points or [])[:4]]
    html = f"<h2>{title or '章节'}</h2><p>{description or '本节内容'}</p><ul>{''.join(key_items)}</ul>"
    return [{
        "layoutType": "edu-keypoints",
        "title": title or "章节",
        "content": [{
            "subTitle": title or "章节",
            "bullets": (key_points or ["核心概念"])[:4],
            "narration": f"本节我们来学习{title or '新内容'}。{description or ''}",
            "icon": "book",
            "colorTheme": "blue",
        }],
        "teacherActions": [],
        "_scene_title": title,
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
) -> tuple[str, dict]:
    """跑 1 件,返回 (name, payload). 任何异常 → fallback."""
    async with sem:
        try:
            payload = await coro_factory()
            return name, payload
        except Exception as e:
            logger.exception(f"[course_bundle] {name} 顶层异常: {e}")
            return name, _fallback_payload(name, f"未捕获: {e}")


# ============================================================
# 公开 API — 一次性
# ============================================================

async def generate_bundle_sync(
    outline: dict[str, Any],
    slots: dict[str, Any],
    portrait: Optional[LearningPortrait] = None,
    enabled_components: Optional[list[str]] = None,
) -> CourseBundle:
    """9 件一次性跑完,返回 CourseBundle(测试/手工用)."""
    ctx = build_bundle_context(outline, slots, portrait)
    factories = _component_dispatcher(ctx, outline, portrait)
    names = enabled_components or list(COMPONENT_NAMES)
    sem = asyncio.Semaphore(BUNDLE_CONCURRENCY)

    tasks = [_run_one_component(n, factories[n], sem) for n in names if n in factories]
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

    Yields:
        {"type": "component_start", "name": ...}      # 开始
        {"type": "component_ready", "name": ..., "payload": ...}  # 完成
        {"type": "bundle_complete", "bundle": CourseBundle.model_dump()}  # 全部完成
    """
    ctx = build_bundle_context(outline, slots, portrait)
    factories = _component_dispatcher(ctx, outline, portrait)
    names = [n for n in (enabled_components or list(COMPONENT_NAMES)) if n in factories]
    sem = asyncio.Semaphore(BUNDLE_CONCURRENCY)

    # 启动所有任务,但 await 时逐件让出
    tasks: dict[str, asyncio.Task] = {}
    for n in names:
        yield {"type": "component_start", "name": n}
        tasks[n] = asyncio.create_task(_run_one_component(n, factories[n], sem))

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
