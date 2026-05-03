"""
课程生成Agent (LLM驱动版)
使用 call_llm_async 进行真实的大模型调用，替换原有的模板匹配逻辑
"""

import asyncio
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional, AsyncGenerator

from state import CourseData, SceneOutline, Slide, SlideContent, SlideElement, SlideBackground, TeacherInfo, SlideV2, SlideContentItemV2
from llm_stream import call_llm_async
from prompts import build_prompt

logger = logging.getLogger(__name__)


@dataclass
class CourseGeneratorConfig:
    """课程生成配置"""
    enable_web_search: bool = True
    enable_pdf_upload: bool = False
    interactive_mode: bool = False
    slide_count_target: int = 6
    teacher_name: str = "星识教师"
    teacher_avatar: str = "🤖"
    agent_mode: str = "preset"  # preset / auto
    voice_id: str = "female-shaonv"
    enable_image: bool = False
    enable_tts: bool = False
    enable_video: bool = False
    first_batch_size: int = 4  # 首次生成的幻灯片数量
    use_v2_slides: bool = True  # 使用 V2 结构化布局格式


class CourseGenerator:
    """
    LLM驱动的课程生成器
    使用 call_llm_async 生成：
    1. 课程标题
    2. 课程大纲（多个 SceneOutline）
    3. 每个大纲的幻灯片内容 + 教师台词
    """

    def __init__(self, config: Optional[CourseGeneratorConfig] = None):
        self.config = config or CourseGeneratorConfig()

    async def generate_course(
            self,
            requirement: str,
            student_id: str = "",
            enable_image: bool = False,
            enable_tts: bool = False,
            voice_id: str = "female-shaonv",
            agent_mode: str = "preset",
            interactive_mode: bool = False,
        ) -> AsyncGenerator[dict[str, Any], None]:
            """
            生成课程，返回SSE事件流

            Events:
                - pdf_analysis: 分析需求中
                - status: 状态更新
                - outline: 单个大纲项
                - outline_progress: 大纲生成完成
                - agent_generation: AI教师团队生成
                - slide_content: 幻灯片内容生成
                - tts_progress: TTS生成进度
                - image_progress: 配图生成进度
                - done: 完成
                - error: 错误
            """
            session_id = str(uuid.uuid4())
            # 使用传入参数覆盖配置
            self.config.voice_id = voice_id
            self.config.agent_mode = agent_mode
            self.config.interactive_mode = interactive_mode
            self.config.enable_image = enable_image
            self.config.enable_tts = enable_tts

            try:
                # ---- Phase 1: 分析需求 ----
                yield {
                    "type": "pdf_analysis",
                    "progress": 5,
                    "data": {"status": "analyzing_requirement"}
                }
                yield {
                    "type": "status",
                    "progress": 8,
                    "data": {"msg": "正在分析学习需求..."}
                }

                # 用LLM生成课程标题
                course_title = await self._call_llm_with_retry(
                    "你是一位课程命名专家。",
                    build_prompt("course_title", requirement=requirement),
                    temperature=0.5,
                )
                course_title = course_title.strip().strip('"\'""')

                yield {
                    "type": "status",
                    "progress": 10,
                    "data": {"msg": f"课程主题: {course_title}"}
                }

                # ---- Phase 2: 生成大纲 ----
                yield {
                    "type": "status",
                    "progress": 15,
                    "data": {"msg": "正在设计课程大纲..."}
                }

                outlines = await self._generate_outlines(requirement)

                for i, outline in enumerate(outlines):
                    yield {
                        "type": "outline",
                        "progress": 20 + int((i / max(len(outlines), 1)) * 15),
                        "data": outline.model_dump()
                    }
                    await asyncio.sleep(0.2)

                yield {
                    "type": "outline_progress",
                    "progress": 35,
                    "data": {"completed": True}
                }

                # ---- Phase 3: 生成AI教师团队 ----
                agent_team: list[dict[str, Any]] = []
                if agent_mode == "auto":
                    yield {
                        "type": "status",
                        "progress": 37,
                        "data": {"msg": "正在生成AI教师团队..."}
                    }
                    agent_team = await self._generate_agent_team(course_title, outlines, requirement)
                    yield {
                        "type": "agent_generation",
                        "progress": 42,
                        "data": {"agents": agent_team, "auto_generated": True}
                    }
                else:
                    agent_team = [{
                        "id": "teacher_preset",
                        "name": self.config.teacher_name,
                        "role": "课程导师",
                        "persona": "经验丰富的AI教师，擅长互动式教学",
                        "avatar": self.config.teacher_avatar,
                        "color": "#6366f1",
                        "voice_id": voice_id,
                        "priority": 0,
                    }]
                    yield {
                        "type": "agent_generation",
                        "progress": 40,
                        "data": {"agents": agent_team, "auto_generated": False}
                    }

                # ---- Phase 4: 生成幻灯片内容（渐进式：先出首批，后出其余） ----
                yield {
                    "type": "status",
                    "progress": 45,
                    "data": {"msg": "正在生成课程内容..."}
                }

                slides: list[Slide] = []
                slides_v2: list[SlideV2] = []
                quiz_data: list[dict[str, Any]] = []
                exercise_data: list[dict[str, Any]] = []
                total = len(outlines)
                first_batch_size = min(self.config.first_batch_size, total)

                # --- 4a: 生成首批幻灯片（供前端立即展示）---
                first_batch_slides: list[Slide] = []
                slides_v2_batch: list[SlideV2] = []
                for i in range(first_batch_size):
                    outline = outlines[i]
                    slide = None
                    slides_v2_batch = []
                    try:
                        if self.config.use_v2_slides:
                            logger.info(f"[generate] 4a V2 outline[{i}] type={outline.type} title={outline.title}")
                            result = await self._generate_scene_content_v2(course_title, outline, i + 1)
                            slides_v2_batch = result.get("slides_v2", [])
                            logger.info(f"[generate] 4a V2 got slides_v2_batch len={len(slides_v2_batch)}")
                            for sv2 in slides_v2_batch:
                                sv2.scene_id = outline.id
                            slides_v2.extend(slides_v2_batch)
                            # quiz/exercise: ALSO generate specialized data for interactive renderers
                            if outline.type in ("quiz", "exercise"):
                                result_v1 = await self._generate_scene_content(course_title, outline, i + 1)
                                if outline.type == "quiz" and result_v1.get("quiz_data"):
                                    result_v1["quiz_data"]["scene_id"] = outline.id
                                    quiz_data.append(result_v1["quiz_data"])
                                if outline.type == "exercise" and result_v1.get("exercise_data"):
                                    result_v1["exercise_data"]["scene_id"] = outline.id
                                    exercise_data.append(result_v1["exercise_data"])
                        else:
                            logger.info(f"[generate] 4a V1 outline[{i}] type={outline.type} title={outline.title}")
                            result = await self._generate_scene_content(course_title, outline, i + 1)
                            slide = result["slide"]
                            slides.append(slide)
                            first_batch_slides.append(slide)
                            if result.get("quiz_data"):
                                quiz_data.append(result["quiz_data"])
                            if result.get("exercise_data"):
                                exercise_data.append(result["exercise_data"])
                    except Exception as e:
                        logger.exception(f"[generate] 4a CRASH at outline[{i}] type={outline.type}: {e}")
                        raise

                    yield {
                        "type": "slide_content",
                        "progress": 45 + int(((i + 1) / total) * 10),
                        "data": {
                            "slide_id": slides_v2_batch[0].title[:8] if slides_v2_batch else (slide.id if slide else outline.title[:8]),
                            "title": slides_v2_batch[0].title if slides_v2_batch else (slide.title if slide else outline.title),
                            "speech_preview": slides_v2_batch[0].content[0].text[:60] if slides_v2_batch and slides_v2_batch[0].content else "",
                            "scene_type": outline.type,
                        }
                    }

                # --- 首批完成：立即yield progressive_batch，前端可开始展示 ---
                try:
                    logger.info(f"[generate] yielding progressive_batch: slides_v2 len={len(slides_v2)}, first_batch_slides len={len(first_batch_slides)}")
                    slides_v2_dumps = [s.model_dump() for s in slides_v2]
                    logger.info(f"[generate] slides_v2 dumps OK, first dump keys: {list(slides_v2_dumps[0].keys()) if slides_v2_dumps else 'empty'}")
                except Exception as e:
                    logger.exception(f"[generate] slides_v2 model_dump failed: {e}, slides_v2 contents: {slides_v2}")
                    slides_v2_dumps = []
                yield {
                    "type": "progressive_batch",
                    "progress": 55,
                    "data": {
                        "batch_index": 0,
                        "slides": [s.model_dump() for s in first_batch_slides],
                        "slides_v2": slides_v2_dumps,
                        "quiz_data": quiz_data.copy(),
                        "exercise_data": exercise_data.copy(),
                        "is_first_batch": True,
                        "total_batches": 2 if total > first_batch_size else 1,
                    }
                }

                # --- 4b: 继续生成剩余幻灯片 ---
                for i in range(first_batch_size, total):
                    outline = outlines[i]
                    try:
                        if self.config.use_v2_slides:
                            logger.info(f"[generate] 4b V2 outline[{i}] type={outline.type}")
                            result = await self._generate_scene_content_v2(course_title, outline, i + 1)
                            new_v2 = result.get("slides_v2", [])
                            for sv2 in new_v2:
                                sv2.scene_id = outline.id
                            slides_v2.extend(new_v2)
                            # quiz/exercise: ALSO generate specialized data for interactive renderers
                            if outline.type in ("quiz", "exercise"):
                                result_v1 = await self._generate_scene_content(course_title, outline, i + 1)
                                if outline.type == "quiz" and result_v1.get("quiz_data"):
                                    result_v1["quiz_data"]["scene_id"] = outline.id
                                    quiz_data.append(result_v1["quiz_data"])
                                if outline.type == "exercise" and result_v1.get("exercise_data"):
                                    result_v1["exercise_data"]["scene_id"] = outline.id
                                    exercise_data.append(result_v1["exercise_data"])
                            if new_v2:
                                yield {
                                    "type": "slide_content",
                                    "progress": 55 + int(((i + 1 - first_batch_size) / max(total - first_batch_size, 1)) * 17),
                                    "data": {
                                        "slide_id": new_v2[0].title[:8],
                                        "title": new_v2[0].title,
                                        "speech_preview": new_v2[0].content[0].text[:60] if new_v2[0].content else "",
                                        "scene_type": outline.type,
                                    }
                                }
                        else:
                            logger.info(f"[generate] 4b V1 outline[{i}] type={outline.type}")
                            result = await self._generate_scene_content(course_title, outline, i + 1)
                            slide = result["slide"]
                            slides.append(slide)
                            if result.get("quiz_data"):
                                quiz_data.append(result["quiz_data"])
                            if result.get("exercise_data"):
                                exercise_data.append(result["exercise_data"])

                            yield {
                                "type": "slide_content",
                                "progress": 55 + int(((i + 1 - first_batch_size) / max(total - first_batch_size, 1)) * 17),
                                "data": {
                                    "slide_id": slide.id,
                                    "title": slide.title,
                                    "speech_preview": slide.speech[:60] + "..." if len(slide.speech) > 60 else slide.speech,
                                    "scene_type": outline.type,
                                }
                            }
                    except Exception as e:
                        logger.exception(f"[generate] 4b CRASH at outline[{i}] type={outline.type}: {e}")
                        raise

                # ---- Phase 5: 配图生成 ----
                if enable_image:
                    yield {
                        "type": "status",
                        "progress": 72,
                        "data": {"msg": "正在为课程生成配图..."}
                    }
                    slides, img_events = await self._generate_images(slides)
                    for evt in img_events:
                        yield evt
                    yield {
                        "type": "status",
                        "progress": 85,
                        "data": {"msg": "配图生成完成"}
                    }
                else:
                    yield {
                        "type": "status",
                        "progress": 72,
                        "data": {"msg": "跳过配图生成"}
                    }

                # ---- Phase 6: TTS语音生成 ----
                tts_audio_urls: dict[str, str] = {}
                if enable_tts:
                    yield {
                        "type": "status",
                        "progress": 87,
                        "data": {"msg": "正在生成教师语音..."}
                    }
                    slides, tts_events, tts_audio_urls = await self._generate_tts(slides)
                    for evt in tts_events:
                        yield evt
                    yield {
                        "type": "status",
                        "progress": 95,
                        "data": {"msg": "语音生成完成"}
                    }
                else:
                    yield {
                        "type": "status",
                        "progress": 87,
                        "data": {"msg": "跳过语音生成"}
                    }

                # ---- Phase 7: 构建最终数据 ----
                teacher = TeacherInfo(
                    name=self.config.teacher_name,
                    avatar=self.config.teacher_avatar,
                    role="课程导师",
                    voice_id=0  # 默认使用晓雅音色
                )

                course_data = CourseData(
                    courseId=f"course_{int(time.time())}_{uuid.uuid4().hex[:8]}",
                    title=course_title,
                    outlines=outlines,
                    slides=slides,
                    slides_v2=slides_v2,
                    teacher=teacher,
                    agent_team=agent_team,
                    quiz_data=quiz_data,
                    exercise_data=exercise_data,
                    tts_audio_urls=tts_audio_urls,
                    metadata={
                        "requirement": requirement,
                        "student_id": student_id,
                        "session_id": session_id,
                        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "agent_mode": agent_mode,
                        "voice_id": voice_id,
                        "interactive_mode": interactive_mode,
                    }
                )

                yield {
                    "type": "done",
                    "progress": 100,
                    "data": course_data.model_dump()
                }

            except Exception as e:
                yield {
                    "type": "error",
                    "error": str(e),
                    "progress": 0,
                }

    # ----------------------------------------------------------------
    # LLM 调用封装
    # ----------------------------------------------------------------

    async def _call_llm_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3,
        temperature: float = 0.5,
    ) -> str:
        """带重试的LLM调用"""
        last_error: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                result = await call_llm_async(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                )
                if result and result.strip():
                    return result.strip()
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.5 * (attempt + 1))
        raise RuntimeError(
            f"LLM调用失败（已重试{max_retries}次）: {last_error}"
        )

    # ----------------------------------------------------------------
    # 课程标题
    # ----------------------------------------------------------------

    async def _generate_course_title(self, requirement: str) -> str:
        """用LLM生成课程标题"""
        title = await self._call_llm_with_retry(
            "你是一位课程命名专家。",
            build_prompt("course_title", requirement=requirement),
            temperature=0.5,
        )
        return title.strip().strip('"\'""')

    # ----------------------------------------------------------------
    # 大纲生成
    # ----------------------------------------------------------------

    async def _generate_outlines(self, requirement: str) -> list[SceneOutline]:
        """用LLM生成课程大纲"""
        raw = await self._call_llm_with_retry(
            "你是一位课程设计专家，严格按JSON格式输出。",
            build_prompt("outline_generation_v3", requirement=requirement, course_type="general"),
            temperature=0.7,
        )
        items = self._extract_json(raw)

        if not isinstance(items, list):
            raise ValueError("LLM返回的不是JSON数组")

        outlines: list[SceneOutline] = []
        for i, item in enumerate(items):
            outlines.append(SceneOutline(
                id=i + 1,
                title=item.get("title", f"第{i+1}节"),
                type=item.get("type", "slide"),
                points=len(item.get("key_points", [])),
                key_points=item.get("key_points", []),
                description=item.get("description", ""),
            ))
        return outlines

    # ----------------------------------------------------------------
    # 场景内容生成（统一入口，支持slide/quiz/exercise/interactive/pbl）
    # ----------------------------------------------------------------

    async def _generate_scene_content(
        self,
        course_title: str,
        outline: SceneOutline,
        slide_index: int,
    ) -> dict[str, Any]:
        """用LLM为单个大纲项生成内容，返回 {slide, quiz_data?, exercise_data?}"""
        prompt_id = "slide_content"
        system_prompt = "你是一位课程内容专家，严格按JSON格式输出。"

        if outline.type == "quiz":
            prompt_id = "quiz_content"
            system_prompt = "你是一位测验出题专家，严格按JSON格式输出。"
        elif outline.type == "exercise":
            prompt_id = "exercise_content"
            system_prompt = "你是一位练习设计专家，严格按JSON格式输出。"
        elif outline.type == "interactive":
            prompt_id = "interactive_content"
            system_prompt = "你是一位交互式学习内容设计专家，严格按JSON格式输出。"
        elif outline.type == "pbl":
            prompt_id = "pbl_content"
            system_prompt = "你是一位PBL项目制学习设计专家，严格按JSON格式输出。"

        try:
            raw = await self._call_llm_with_retry(
                system_prompt,
                build_prompt(
                    prompt_id,
                    course_title=course_title,
                    outline_title=outline.title,
                    outline_description=outline.description,
                    key_points=", ".join(outline.key_points) if outline.key_points else outline.title,
                ),
                temperature=0.6,
            )
            data = self._extract_json(raw)
        except Exception:
            return {"slide": self._fallback_slide(outline, slide_index)}

        # 构建幻灯片元素
        elements: list[SlideElement] = []
        quiz_result: Optional[dict[str, Any]] = None
        exercise_result: Optional[dict[str, Any]] = None

        if outline.type == "quiz":
            questions = data.get("questions", [])
            for qi, q in enumerate(questions):
                elements.append(SlideElement(
                    type="text",
                    content=f"📝 Q{qi + 1}: {q.get('question', '')}",
                    left=100, top=80 + qi * 90, width=750, height=30,
                ))
            quiz_result = {
                "id": slide_index,
                "scene_id": outline.id,
                "title": data.get("title", outline.title),
                "questions": questions,
                "speech": data.get("speech", ""),
            }
        elif outline.type == "exercise":
            exercises = data.get("exercises", [])
            for ei, ex in enumerate(exercises):
                elements.append(SlideElement(
                    type="text",
                    content=f"✏️ 练习{ei + 1}: {ex.get('instruction', '')}",
                    left=100, top=80 + ei * 80, width=750, height=70,
                ))
            exercise_result = {
                "id": slide_index,
                "scene_id": outline.id,
                "title": data.get("title", outline.title),
                "exercises": exercises,
                "speech": data.get("speech", ""),
            }
        else:
            # 处理增强版幻灯片元素
            for elem_data in data.get("elements", []):
                try:
                    elem_type = elem_data.get("type", "text")
                    element = SlideElement(
                        type=elem_type,
                        id=elem_data.get("id", f"elem_{len(elements) + 1}"),
                        content=elem_data.get("content", ""),
                        left=self._normalize_coord(elem_data.get("left", 100)),
                        top=self._normalize_coord(elem_data.get("top", 100)),
                        width=self._normalize_coord(elem_data.get("width", 400)),
                        height=self._normalize_coord(elem_data.get("height", 100)),
                        default_font_name=elem_data.get("default_font_name", "Microsoft YaHei"),
                        default_color=elem_data.get("default_color", "#333333"),
                        fill=elem_data.get("fill", ""),
                        opacity=elem_data.get("opacity", 1.0),
                        rotate=elem_data.get("rotate", 0),
                        # Shape
                        shape_name=elem_data.get("shape_name", ""),
                        path=elem_data.get("path", ""),
                        view_box=elem_data.get("viewBox", [0, 0, 100, 100]),
                        # Line
                        line_color=elem_data.get("line_color", "#333333"),
                        line_style=elem_data.get("line_style", "solid"),
                        points=elem_data.get("points", []),
                        # Chart
                        chart_type=elem_data.get("chart_type", ""),
                        chart_data=elem_data.get("chart_data", {}),
                        theme_colors=elem_data.get("theme_colors", []),
                        # LaTeX
                        latex=elem_data.get("latex", ""),
                        # Table
                        table_data=elem_data.get("table_data", []),
                        col_widths=elem_data.get("col_widths", []),
                        # Image/Video
                        image_url=elem_data.get("image_url", ""),
                        video_url=elem_data.get("video_url", ""),
                        poster=elem_data.get("poster", ""),
                        # Link
                        link=elem_data.get("link", {}),
                        # Shadow/Outline
                        shadow=elem_data.get("shadow", {}),
                        outline=elem_data.get("outline", {}),
                    )
                    elements.append(element)
                except Exception as e:
                    logger.warning(f"Failed to parse element: {e}")
                    continue

        slide = Slide(
            id=slide_index,
            scene_id=outline.id,
            title=data.get("title", outline.title),
            content=SlideContent(elements=elements),
            speech=data.get("speech", f"现在我们来学习{outline.title}的内容。"),
            image_prompt=data.get("image_prompt", ""),
            remark=data.get("remark", ""),
        )
        return {"slide": slide, "quiz_data": quiz_result, "exercise_data": exercise_result}

    async def _generate_scene_content_v2(
        self,
        course_title: str,
        outline: SceneOutline,
        slide_index: int,
    ) -> dict[str, Any]:
        """用LLM生成V2格式幻灯片内容（结构化布局）—— 强容错版本"""
        try:
            raw = await self._call_llm_with_retry(
                "你是一位课程内容专家，严格按JSON格式输出。",
                build_prompt(
                    "slide_content_v2",
                    course_title=course_title,
                    scene_type=outline.type,
                    outline_title=outline.title,
                    outline_description=outline.description,
                    key_points=", ".join(outline.key_points) if outline.key_points else outline.title,
                ),
                temperature=0.6,
            )
        except Exception as e:
            logger.error(f"[_generate_scene_content_v2] LLM调用失败 outline={outline.title}: {e}")
            fallback = self._fallback_slide_v2(outline)
            return {"slides_v2": [fallback]}

        # --- 第一层：JSON解析容错 ---
        try:
            data = self._extract_json(raw)
        except Exception as e:
            logger.error(f"[_generate_scene_content_v2] JSON解析失败，原始响应前500字符: {repr(raw[:500])}")
            fallback = self._fallback_slide_v2(outline)
            return {"slides_v2": [fallback]}

        # 确保 data 是字典且包含 slides 字段
        if not isinstance(data, dict):
            logger.error(f"[_generate_scene_content_v2] data 不是字典类型，是 {type(data)}，原始响应前300字符: {repr(str(data)[:300])}")
            fallback = self._fallback_slide_v2(outline)
            return {"slides_v2": [fallback]}

        slides_data = data.get("slides")
        if not slides_data:
            logger.error(f"[_generate_scene_content_v2] data 中缺少 slides 字段或为空，data keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
            fallback = self._fallback_slide_v2(outline)
            return {"slides_v2": [fallback]}

        if not isinstance(slides_data, list):
            logger.error(f"[_generate_scene_content_v2] slides 不是列表，是 {type(slides_data)}")
            fallback = self._fallback_slide_v2(outline)
            return {"slides_v2": [fallback]}

        # --- 第二层：逐页解析容错 ---
        slides_v2: list[SlideV2] = []
        for idx, slide_data in enumerate(slides_data):
            try:
                if not isinstance(slide_data, dict):
                    logger.warning(f"[_generate_scene_content_v2] slides[{idx}] 不是字典，是 {type(slide_data)}，跳过")
                    continue

                # 安全提取字段，缺失则用默认值
                slide_title = slide_data.get("title") or outline.title or f"知识点讲解 {idx + 1}"
                layout_type = slide_data.get("layoutType") or "two-column"

                # 校验 layout_type 合法性
                allowed_layouts = {"title-only", "two-column", "grid-cards", "header-content", "quote-highlight"}
                if layout_type not in allowed_layouts:
                    logger.warning(f"[_generate_scene_content_v2] slides[{idx}] layoutType={layout_type} invalid, forcing two-column")
                    layout_type = "two-column"

                # --- 第三层：逐卡片解析容错 ---
                content_items: list[SlideContentItemV2] = []
                raw_content = slide_data.get("content") or []

                if not isinstance(raw_content, list):
                    logger.warning(f"[_generate_scene_content_v2] slides[{idx}] content 不是列表，是 {type(raw_content)}，设为空")
                    raw_content = []

                for cidx, item_data in enumerate(raw_content):
                    try:
                        if not isinstance(item_data, dict):
                            logger.warning(f"[_generate_scene_content_v2] slides[{idx}].content[{cidx}] 不是字典，跳过")
                            continue

                        icon = item_data.get("icon", "book")
                        if icon not in {"book", "lightbulb", "code", "check", "star", "question", "warning", "info"}:
                            icon = "book"

                        color_theme = item_data.get("colorTheme", "blue")
                        if color_theme not in {"blue", "yellow", "green", "purple", "orange"}:
                            color_theme = "blue"

                        content_item = SlideContentItemV2(
                            sub_title=item_data.get("subTitle") or "",
                            text=item_data.get("text") or "",
                            icon=icon,
                            color_theme=color_theme,
                            code_snippet=item_data.get("codeSnippet") or "",
                            image_url=item_data.get("imageUrl") or "",
                        )
                        content_items.append(content_item)
                    except Exception as e:
                        logger.warning(f"[_generate_scene_content_v2] slides[{idx}].content[{cidx}] 解析异常: {e}，跳过该卡片")
                        continue

                slide_v2 = SlideV2(
                    layout_type=layout_type,
                    title=slide_title,
                    content=content_items,
                )
                slides_v2.append(slide_v2)
            except Exception as e:
                logger.warning(f"[_generate_scene_content_v2] slides[{idx}] 解析异常: {e}，跳过该页")
                continue

        # --- 最终兜底：没有任何有效幻灯片时 ---
        if not slides_v2:
            logger.error(f"[_generate_scene_content_v2] 所有幻灯片解析均失败，使用兜底页，原始 slides_data: {repr(str(slides_data)[:500])}")
            fallback = self._fallback_slide_v2(outline)
            return {"slides_v2": [fallback]}

        return {"slides_v2": slides_v2}

    def _fallback_slide_v2(self, outline: SceneOutline) -> SlideV2:
        """V2格式降级幻灯片"""
        return SlideV2(
            layout_type="two-column",
            title=outline.title,
            content=[
                SlideContentItemV2(
                    sub_title="概述",
                    text=f"本节将介绍{outline.title}的相关概念和应用",
                    icon="book",
                    color_theme="blue",
                )
            ],
        )

    async def _generate_agent_team(
        self,
        course_title: str,
        outlines: list[SceneOutline],
        requirement: str,
    ) -> list[dict[str, Any]]:
        """用LLM自动生成AI教师团队"""
        outlines_json = json.dumps(
            [{"id": o.id, "title": o.title, "type": o.type, "description": o.description}
             for o in outlines],
            ensure_ascii=False,
        )
        try:
            raw = await self._call_llm_with_retry(
                "你是一位教学团队设计专家，严格按JSON格式输出。",
                build_prompt(
                    "agent_team_generation",
                    course_title=course_title,
                    outlines=outlines_json,
                    requirement=requirement,
                ),
                temperature=0.8,
            )
            data = self._extract_json(raw)
            agents: list[dict[str, Any]] = data.get("agents", [])
            for i, agent in enumerate(agents):
                agent["voice_id"] = i  # 0-4 对应晓雅/云起/雨辰/苏格拉底/雅典娜
                agent.setdefault("id", f"teacher_{i + 1}")
                agent.setdefault("color", "#6366f1")
            return agents
        except Exception as e:
            logger.warning(f"Agent team generation failed: {e}")
            return [{
                "id": "teacher_1",
                "name": "星识教师",
                "role": "课程导师",
                "persona": "经验丰富的AI教师，善于因材施教",
                "avatar": "🤖",
                "color": "#6366f1",
                "voice_id": 0,
                "priority": 0,
            }]

    # ----------------------------------------------------------------
    # Quiz 评分
    # ----------------------------------------------------------------

    async def grade_quiz_answers(
        self,
        questions: list[dict[str, Any]],
        student_answers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """用LLM批改Quiz答案"""
        # 先做规则匹配（如果答案格式标准）
        correct_count = 0
        total = len(questions)
        feedback_list: list[dict[str, Any]] = []

        for i, q in enumerate(questions):
            student_ans = -1
            for sa in student_answers:
                if sa.get("question_index") == i:
                    student_ans = sa.get("selected_option", -1)
                    break
            correct_ans = q.get("correct_answer", 0)
            is_correct = (student_ans == correct_ans)
            if is_correct:
                correct_count += 1

            # 简单反馈
            if is_correct:
                fb = f"正确！{q.get('explanation', '回答得很好')}"
            elif student_ans < 0:
                fb = f"未作答。正确答案是{q.get('options', [])[correct_ans] if correct_ans < len(q.get('options', [])) else ''}。{q.get('explanation', '')}"
            else:
                fb = f"回答错误。正确答案是{q.get('options', [])[correct_ans] if correct_ans < len(q.get('options', [])) else ''}。{q.get('explanation', '')}"
            feedback_list.append({
                "question_index": i,
                "is_correct": is_correct,
                "feedback": fb,
                "correct_option": correct_ans,
            })

        total_pct = round(correct_count / total * 100, 1) if total > 0 else 0
        return {
            "scores": [1 if f["is_correct"] else 0 for f in feedback_list],
            "total": total_pct,
            "passed": total_pct >= 60,
            "correct_count": correct_count,
            "total_count": total,
            "feedback_per_question": feedback_list,
        }

    async def _generate_images(self, slides: list[Slide]) -> tuple[list[Slide], list[dict]]:
        """为每张幻灯片生成配图（串行调用MiniMax image-01）
        返回: (更新后的slides列表, 事件列表)
        """
        from media_generation import generate_image

        updated: list[Slide] = []
        events: list[dict] = []
        for i, slide in enumerate(slides):
            if slide.image_prompt:
                try:
                    image_url = await generate_image(slide.image_prompt)
                    for elem in slide.content.elements:
                        if elem.type == "image" or not elem.image_url:
                            elem.image_url = image_url
                            break
                    if slide.content.elements:
                        slide.content.elements[0].image_url = image_url

                    events.append({
                        "type": "image_progress",
                        "progress": 72 + int(((i + 1) / len(slides)) * 13),
                        "data": {"slide_id": slide.id, "image_url": image_url},
                    })
                except Exception as e:
                    logger.warning(f"Image generation failed for slide {slide.id}: {e}")
                    events.append({
                        "type": "image_progress",
                        "progress": 72 + int(((i + 1) / len(slides)) * 13),
                        "data": {"slide_id": slide.id, "error": str(e)},
                    })
            else:
                events.append({
                    "type": "image_progress",
                    "progress": 72 + int(((i + 1) / len(slides)) * 13),
                    "data": {"slide_id": slide.id, "skipped": True},
                })
            updated.append(slide)

        return updated, events

    async def _generate_tts(self, slides: list[Slide]) -> tuple[list[Slide], list[dict], dict[str, str]]:
        """为每张幻灯片生成教师语音（串行调用MiniMax TTS）
        返回: (更新后的slides列表, 事件列表, audio_urls映射)
        """
        from media_generation import generate_tts

        updated: list[Slide] = []
        events: list[dict] = []
        audio_urls: dict[str, str] = {}
        for i, slide in enumerate(slides):
            if slide.speech:
                try:
                    audio_bytes = await generate_tts(
                        slide.speech,
                        voice_id=self.config.voice_id,
                    )

                    audio_dir = os.path.join(os.path.dirname(__file__), "storage", "audio")
                    os.makedirs(audio_dir, exist_ok=True)
                    filename = f"tts_{uuid.uuid4().hex}.mp3"
                    filepath = os.path.join(audio_dir, filename)
                    with open(filepath, "wb") as f:
                        f.write(audio_bytes)

                    audio_url = f"/storage/audio/{filename}"
                    audio_urls[str(slide.id)] = audio_url
                    for elem in slide.content.elements:
                        if elem.type == "audio" or not elem.audio_url:
                            elem.audio_url = audio_url
                            break
                    if slide.content.elements:
                        slide.content.elements[0].audio_url = audio_url

                    events.append({
                        "type": "tts_progress",
                        "progress": 87 + int(((i + 1) / len(slides)) * 8),
                        "data": {"slide_id": slide.id, "audio_url": audio_url},
                    })
                except Exception as e:
                    logger.warning(f"TTS generation failed for slide {slide.id}: {e}")
                    events.append({
                        "type": "tts_progress",
                        "progress": 87 + int(((i + 1) / len(slides)) * 8),
                        "data": {"slide_id": slide.id, "error": str(e)},
                    })
            else:
                events.append({
                    "type": "tts_progress",
                    "progress": 87 + int(((i + 1) / len(slides)) * 8),
                    "data": {"slide_id": slide.id, "skipped": True},
                })
            updated.append(slide)

        return updated, events, audio_urls

    def _fallback_slide(self, outline: SceneOutline, slide_index: int) -> Slide:
        """LLM生成失败时的保底幻灯片"""
        return Slide(
            id=slide_index,
            title=outline.title,
            content=SlideContent(elements=[
                SlideElement(type="text", content=outline.title, left=100, top=100, width=600, height=60),
                SlideElement(type="text", content="\n".join(f"• {kp}" for kp in outline.key_points),
                             left=100, top=180, width=500, height=250),
            ]),
            speech=f"现在我们来学习{outline.title}的内容。",
            image_prompt="",
        )

    # ----------------------------------------------------------------
    # JSON 解析
    # ----------------------------------------------------------------

    @staticmethod
    def _extract_json(text: str) -> Any:
        """从LLM响应中提取JSON，兼容markdown代码块格式"""
        text = text.strip()
        # 移除 markdown 代码块标记
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        # 尝试找到JSON数组或对象
        text = text.strip()
        if text.startswith("["):
            return json.loads(text)
        if text.startswith("{"):
            return json.loads(text)
        match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"无法从LLM响应中解析JSON: {text[:200]}")

    @staticmethod
    def _normalize_coord(value: Any, canvas_dim: float = 1000) -> float:
        """将LLM返回的坐标值规范化为数值"""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.strip()
            is_pct = "%" in cleaned
            cleaned = cleaned.replace("px", "").replace("%", "").strip()
            try:
                num = float(cleaned)
                if is_pct:
                    return round(num / 100 * canvas_dim, 1)
                return num
            except (ValueError, TypeError):
                return 100.0
        return 100.0


# 全局实例
_course_generator_instance: Optional[CourseGenerator] = None


def get_course_generator() -> CourseGenerator:
    """获取课程生成器实例"""
    global _course_generator_instance
    if _course_generator_instance is None:
        _course_generator_instance = CourseGenerator()
    return _course_generator_instance
