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

from state import CourseData, SceneOutline, Slide, SlideContent, SlideElement, SlideBackground, TeacherInfo, SlideV2, SlideContentItemV2, TeacherAction
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
    first_batch_size: int = 5  # 首次生成的幻灯片数量（生成5个后前端即可进入课堂）
    use_v2_slides: bool = True  # 使用 V2 结构化布局格式
    # MiniMax PPT 混合生成配置
    enable_minimax_ppt: bool = True   # 启用 MiniMax PPT 混合生成
    minimax_ppt_ratio: float = 0.7    # MiniMax PPT 占比（0~1）
    # 用户选择的AI教师详细信息
    teacher_profession: str = ""
    teacher_personality: str = ""
    teacher_teaching_style: str = ""
    teacher_icon: str = ""
    teacher_system_prompt: str = ""
    teacher_greeting: str = ""


class CourseGenerator:
    """
    LLM驱动的课程生成器
    使用 call_llm_async 生成：
    1. 课程标题
    2. 课程大纲（多个 SceneOutline）
    3. 每个大纲的幻灯片内容 + 教师台词
    """

    # V2幻灯片数量上限
    MAX_SLIDES_V2 = 50

    # 15种PPT布局：11文字 + 2图片 + 2视频
    TEXT_LAYOUTS = {
        "spotlight-focus", "kinetic-type", "isometric-cards", "orbit-ring",
        "gradient-split", "dark-header", "circle-radial", "stair-step",
        "quote-wall", "info-graphic", "floating-overlap",
    }
    IMAGE_LAYOUTS = {
        "magazine-cover", "photo-story",
    }
    VIDEO_LAYOUTS = {
        "media-showcase", "video-lecture",
    }
    ALL_LAYOUTS = TEXT_LAYOUTS | IMAGE_LAYOUTS | VIDEO_LAYOUTS

    def __init__(self, config: Optional[CourseGeneratorConfig] = None):
        self.config = config or CourseGeneratorConfig()
        self._used_layouts: set[str] = set()
        self._layout_pool: list[str] = []

    async def generate_course(
            self,
            requirement: str,
            student_id: str = "",
            enable_image: bool = False,
            enable_tts: bool = False,
            enable_video: bool = False,
            voice_id: str = "female-shaonv",
            agent_mode: str = "preset",
            interactive_mode: bool = False,
            enable_pdf_upload: bool = False,
            pdf_text: str = "",
            enable_web_search: bool = True,
            enable_minimax_ppt: bool = True,
            minimax_ppt_ratio: float = 0.7,
            teacher_name: str = "",
            teacher_avatar: str = "",
            teacher_profession: str = "",
            teacher_personality: str = "",
            teacher_teaching_style: str = "",
            teacher_icon: str = "",
            teacher_system_prompt: str = "",
            teacher_greeting: str = "",
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
            self.config.enable_video = enable_video
            self.config.enable_pdf_upload = enable_pdf_upload
            self.config.enable_web_search = enable_web_search
            self.config.enable_minimax_ppt = enable_minimax_ppt
            self.config.minimax_ppt_ratio = minimax_ppt_ratio
            self._pdf_text = pdf_text  # 存储PDF文本，供 _generate_outlines / _generate_scene_content_v2 使用
            # 用户选择的AI教师信息
            if teacher_name:
                self.config.teacher_name = teacher_name
            if teacher_avatar:
                self.config.teacher_avatar = teacher_avatar
            self.config.teacher_profession = teacher_profession
            self.config.teacher_personality = teacher_personality
            self.config.teacher_teaching_style = teacher_teaching_style
            self.config.teacher_icon = teacher_icon
            self.config.teacher_system_prompt = teacher_system_prompt
            self.config.teacher_greeting = teacher_greeting

            # 根据用户选项构建可用布局池
            available_layouts = set(self.TEXT_LAYOUTS)
            if enable_image:
                available_layouts |= self.IMAGE_LAYOUTS
            if enable_video:
                available_layouts |= self.VIDEO_LAYOUTS
            self._active_layouts = available_layouts
            logger.info(f"[generate] available layouts: {len(available_layouts)} (image={enable_image}, video={enable_video})")

            # 构建给LLM的可用布局说明文本
            layout_desc_lines = []
            for lt in sorted(self.TEXT_LAYOUTS):
                layout_desc_lines.append(f"- {lt}: 文字布局")
            if enable_image:
                layout_desc_lines.append("- magazine-cover: 杂志封面，全屏背景图+文字叠加（图片布局，需提供imageUrl）")
                layout_desc_lines.append("- photo-story: 照片故事，左大图+右侧文字（图片布局，需提供imageUrl）")
            if enable_video:
                layout_desc_lines.append("- media-showcase: 媒体展示舞台，中央视频+底部描述（视频布局，需提供videoUrl）")
                layout_desc_lines.append("- video-lecture: 视频讲义，左侧视频+右侧要点（视频布局，需提供videoUrl）")
            self._layout_descriptions = "\n".join(layout_desc_lines)

            # 初始化课程级布局轮询池
            import random
            self._used_layouts.clear()
            self._layout_pool = list(available_layouts)
            random.shuffle(self._layout_pool)

            try:
                # ---- Phase 1: 分析需求（精简：跳过独立的标题生成和需求分析LLM调用）----
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

                # 直接从用户输入提取课程标题（节省1次LLM调用）
                # 取需求文本前30字或第一行作为标题
                raw_title = requirement.strip().split('\n')[0][:30].strip()
                course_title = raw_title if len(raw_title) >= 4 else "自定义课程"

                yield {
                    "type": "status",
                    "progress": 10,
                    "data": {"msg": f"课程主题: {course_title}"}
                }

                # ---- Phase 1.5: 需求分析（精简：跳过LLM分析，使用轻量兜底）----
                # 需求分析的结果对大纲生成并非关键输入，大纲prompt本身已包含需求文本
                requirement_analysis = {
                    "learning_goals": [f"学习{course_title}"],
                    "target_audience": "初学者",
                    "difficulty": "basic",
                    "prerequisites": [],
                    "estimated_duration": "30分钟",
                    "key_topics": [course_title],
                    "suggested_scene_types": ["slide", "quiz"],
                    "analysis_summary": "基于用户需求生成课程",
                }
                yield {
                    "type": "requirement_analysis",
                    "progress": 12,
                    "data": requirement_analysis,
                }

                # ---- Phase 1.6: 网络搜索（获取最新资料）----
                web_search_sources: list[dict[str, str]] = []
                if self.config.enable_web_search:
                    yield {
                        "type": "status",
                        "progress": 12,
                        "data": {"msg": "正在搜索相关资料..."}
                    }
                    try:
                        from app.services.teacher.web_search import search_minimax, search_web
                        search_resp = await search_minimax(course_title)
                        if search_resp and search_resp.answer:
                            web_search_sources.append({
                                "title": f"MiniMax: {course_title}",
                                "url": "https://www.minimaxi.com"
                            })
                        else:
                            tavily_resp = await search_web(course_title)
                            web_search_sources = [
                                {"title": r.title, "url": r.url}
                                for r in tavily_resp.results[:5]
                                if r.title and r.url
                            ]
                        if web_search_sources:
                            yield {
                                "type": "web_search",
                                "progress": 13,
                                "sources_count": len(web_search_sources),
                                "sources": web_search_sources,
                            }
                    except Exception as e:
                        logger.warning(f"[generate] web search failed for course title: {e}")

                # ---- Phase 2: 生成大纲 ----
                yield {
                    "type": "status",
                    "progress": 15,
                    "data": {"msg": "正在设计课程大纲..."}
                }

                outlines = await self._generate_outlines(requirement, requirement_analysis)

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
                    # 预设模式：使用用户选择的教师配置
                    agent_team = [{
                        "id": "teacher_preset",
                        "name": self.config.teacher_name,
                        "role": "课程导师",
                        "persona": self.config.teacher_personality or "经验丰富的AI教师，擅长互动式教学",
                        "avatar": self.config.teacher_avatar,
                        "color": "#6366f1",
                        "voice_id": voice_id,
                        "priority": 0,
                        "profession": self.config.teacher_profession,
                        "personality": self.config.teacher_personality,
                        "teaching_style": self.config.teacher_teaching_style,
                        "icon": self.config.teacher_icon,
                        "system_prompt": self.config.teacher_system_prompt,
                        "greeting": self.config.teacher_greeting,
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
                interactive_data: list[dict[str, Any]] = []
                code_data: list[dict[str, Any]] = []
                total = len(outlines)
                first_batch_size = min(self.config.first_batch_size, total)

                # --- 4a: 生成首批幻灯片（供前端立即展示）---
                # 策略：并行生成outline内容（最多3并发），一旦slides_v2达到5张立即触发first_batch_complete进入课堂
                # 为加速首批：跳过网络搜索、跳过图片生成
                first_batch_slides: list[Slide] = []
                slides_v2_batch: list[SlideV2] = []
                first_batch_done_index = -1

                # 限制并发数，避免压垮LLM API
                _gen_sem = asyncio.Semaphore(3)

                async def _gen_one_outline(i: int, outline: SceneOutline) -> dict[str, Any]:
                    """单个outline的生成任务（受semaphore限制并发）"""
                    async with _gen_sem:
                        slide: Optional[Slide] = None
                        slides_v2_batch_local: list[SlideV2] = []
                        quiz_result_local = None
                        exercise_result_local = None
                        interactive_result_local = None
                        code_result_local = None
                        whiteboard_desc = None
                        whiteboard_speech = None
                        whiteboard_actions_local = None

                        try:
                            if self.config.use_v2_slides:
                                prev_title = outlines[i - 1].title if i > 0 else "（本课程第一节）"
                                next_title = outlines[i + 1].title if i + 1 < total else "（本课程最后一节）"
                                result = await self._generate_scene_content_v2(
                                    course_title, outline, i + 1, prev_title, next_title,
                                    skip_web_search=True
                                )
                                slides_v2_batch_local = result.get("slides_v2", [])
                                for sv2 in slides_v2_batch_local:
                                    sv2.scene_id = outline.id

                                quiz_result_local = result.get("quiz_data")
                                exercise_result_local = result.get("exercise_data")
                                if outline.type == "interactive":
                                    interactive_result_local = result.get("interactive_data")
                                if outline.type == "code":
                                    code_result_local = result.get("code_data")
                                if outline.type == "whiteboard":
                                    whiteboard_desc = result.get("whiteboard_description", outline.description)
                                    whiteboard_speech = result.get("speech", f"现在我们来学习{outline.title}的内容。")
                                    whiteboard_actions_local = result.get("whiteboard_actions")
                            else:
                                result = await self._generate_scene_content(course_title, outline, i + 1)
                                slide = result["slide"]
                        except Exception as e:
                            logger.exception(f"[generate] 4a FAILED at outline[{i}] type={outline.type}: {e}")
                            # 返回错误标记，不抛异常，让外层跳过此outline
                            return {"_error": True, "_error_msg": str(e), "i": i, "outline": outline}

                        return {
                            "i": i,
                            "outline": outline,
                            "slide": slide,
                            "slides_v2_batch": slides_v2_batch_local,
                            "quiz_result": quiz_result_local,
                            "exercise_result": exercise_result_local,
                            "interactive_result": interactive_result_local,
                            "code_result": code_result_local,
                            "whiteboard_desc": whiteboard_desc,
                            "whiteboard_speech": whiteboard_speech,
                            "whiteboard_actions": whiteboard_actions_local,
                        }

                # 分批并行生成，每批最多3个，按顺序收集结果
                batch_step = 3
                for batch_start in range(0, min(first_batch_size, total), batch_step):
                    batch_end = min(batch_start + batch_step, first_batch_size)
                    tasks = [asyncio.create_task(_gen_one_outline(i, outlines[i])) for i in range(batch_start, batch_end)]
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                    for raw_res in batch_results:
                        if isinstance(raw_res, Exception):
                            logger.warning(f"[generate] 4a batch task exception: {raw_res}")
                            continue
                        res = raw_res
                        # 跳过失败的outline
                        if res.get("_error"):
                            logger.warning(f"[generate] 4a skipping failed outline[{res['i']}]: {res.get('_error_msg')}")
                            continue
                        i = res["i"]
                        outline = res["outline"]
                        slide = res["slide"]
                        sv2_batch = res["slides_v2_batch"]

                        # 累积结果到主列表
                        if sv2_batch:
                            slides_v2.extend(sv2_batch)
                        if slide:
                            slides.append(slide)
                            first_batch_slides.append(slide)
                        if res["quiz_result"] and outline.type == "quiz":
                            res["quiz_result"]["scene_id"] = outline.id
                            quiz_data.append(res["quiz_result"])
                        if res["exercise_result"]:
                            res["exercise_result"]["scene_id"] = outline.id
                            exercise_data.append(res["exercise_result"])
                        if res["interactive_result"]:
                            res["interactive_result"]["scene_id"] = outline.id
                            interactive_data.append(res["interactive_result"])
                        if res["code_result"]:
                            res["code_result"]["scene_id"] = outline.id
                            code_data.append(res["code_result"])
                        if res["whiteboard_desc"] is not None:
                            outline.whiteboard_description = res["whiteboard_desc"]
                            outline.speech = res["whiteboard_speech"] or outline.speech
                        if res.get("whiteboard_actions"):
                            outline.whiteboard_actions = res["whiteboard_actions"]

                        yield {
                            "type": "slide_content",
                            "progress": 45 + int(((i + 1) / total) * 10),
                            "data": {
                                "slide_id": sv2_batch[0].title[:8] if sv2_batch else (slide.id if slide else outline.title[:8]),
                                "title": sv2_batch[0].title if sv2_batch else (slide.title if slide else outline.title),
                                "speech_preview": sv2_batch[0].content[0].text[:60] if sv2_batch and sv2_batch[0].content else "",
                                "scene_type": outline.type,
                            }
                        }

                        # 动态检测：一旦生成好5张PPT，立即触发首批完成
                        if len(slides_v2) >= 5:
                            first_batch_done_index = i
                            logger.info(f"[generate] 4a early break at outline[{i}], slides_v2={len(slides_v2)} >= 5")
                            break

                        # 达到上限，提前结束首批
                        if len(slides_v2) >= self.MAX_SLIDES_V2:
                            first_batch_done_index = i
                            logger.info(f"[generate] 4a early break at outline[{i}], slides_v2={len(slides_v2)} reached MAX_SLIDES_V2")
                            break

                    if first_batch_done_index >= 0:
                        break
                else:
                    # 循环自然结束（所有outline处理完毕）
                    first_batch_done_index = total - 1

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
                        "interactive_data": interactive_data.copy(),
                        "code_data": code_data.copy(),
                        "is_first_batch": True,
                        "total_batches": 2 if total > first_batch_done_index + 1 else 1,
                    }
                }

                # --- 只取前5个 slides_v2 用于首批进入课堂，剩余放入pending ---
                first_batch_slides_v2 = slides_v2[:5]
                remaining_slides_v2 = slides_v2[5:]
                logger.info(f"[generate] first_batch_complete: first_batch_slides_v2={len(first_batch_slides_v2)}, remaining={len(remaining_slides_v2)}")

                # --- 首批完成：通知前端可以进入课堂 ---
                # 构建首批的 teacher 信息（使用用户选择的教师配置）
                first_batch_teacher = {
                    "name": self.config.teacher_name,
                    "avatar": self.config.teacher_avatar,
                    "role": "课程导师",
                    "voice_id": self.config.voice_id,
                    "profession": self.config.teacher_profession,
                    "personality": self.config.teacher_personality,
                    "teaching_style": self.config.teacher_teaching_style,
                    "icon": self.config.teacher_icon,
                    "system_prompt": self.config.teacher_system_prompt,
                    "greeting": self.config.teacher_greeting,
                }
                yield {
                    "type": "first_batch_complete",
                    "progress": 55,
                    "data": {
                        "session_id": session_id,
                        "course_title": course_title,
                        "outlines": [o.model_dump() for o in outlines],
                        "agent_team": agent_team,
                        "slides": [s.model_dump() for s in first_batch_slides],
                        "slides_v2": [s.model_dump() for s in first_batch_slides_v2],
                        "quiz_data": quiz_data.copy(),
                        "exercise_data": exercise_data.copy(),
                        "interactive_data": interactive_data.copy(),
                        "code_data": code_data.copy(),
                        "generated_count": first_batch_done_index + 1,
                        "total_outlines": total,
                        "teacher": first_batch_teacher,
                    }
                }

                # --- 保存首批后的pending状态到数据库 ---
                logger.info(f"[generate] Saving initial generation status for course_id={session_id}, remaining={len(remaining_slides_v2)}")
                try:
                    from db import save_course_generation_status
                    save_result = save_course_generation_status(
                        course_id=session_id,
                        total_outlines=total,
                        generated_count=first_batch_done_index + 1,
                        pending_slides_v2=[s.model_dump() for s in remaining_slides_v2],  # 剩余的slides通过轮询获取
                        pending_quiz_data=[],
                        pending_exercise_data=[],
                        is_complete=0
                    )
                    logger.info(f"[generate] Initial generation status saved: {save_result}")
                except Exception as e:
                    logger.exception(f"[generate] Failed to save initial generation status: {e}")

                # --- 4b: 继续生成剩余幻灯片 ---
                # 初始化 pending 列表时包含 remaining_slides_v2，避免被后续 update 覆盖丢失
                pending_slides_v2_for_db: list[dict] = [s.model_dump() for s in remaining_slides_v2]
                pending_quiz_data_for_db: list[dict] = []
                pending_exercise_data_for_db: list[dict] = []
                logger.info(f"[generate] 4b starting: pending_slides_v2_for_db initialized with {len(pending_slides_v2_for_db)} slides from remaining_slides_v2")
                for i in range(first_batch_done_index + 1, total):
                    # 达到50页上限，提前结束
                    if len(slides_v2) >= self.MAX_SLIDES_V2:
                        logger.info(f"[generate] 4b early stop at outline[{i}], slides_v2={len(slides_v2)} reached MAX_SLIDES_V2={self.MAX_SLIDES_V2}")
                        break
                    outline = outlines[i]
                    try:
                        if self.config.use_v2_slides:
                            logger.info(f"[generate] 4b V2 outline[{i}] type={outline.type}")
                            prev_title = outlines[i - 1].title if i > 0 else "（本课程第一节）"
                            next_title = outlines[i + 1].title if i + 1 < total else "（本课程最后一节）"
                            result = await self._generate_scene_content_v2(course_title, outline, i + 1, prev_title, next_title)
                            new_v2 = result.get("slides_v2", [])
                            for sv2 in new_v2:
                                sv2.scene_id = outline.id
                            slides_v2.extend(new_v2)

                            # Push newly generated slides to pending list for frontend polling
                            if new_v2:
                                pending_slides_v2_for_db.extend([s.model_dump() for s in new_v2])
                                try:
                                    from db import update_course_generation_status
                                    update_course_generation_status(
                                        course_id=session_id,
                                        pending_slides_v2=pending_slides_v2_for_db.copy()
                                    )
                                except Exception as e:
                                    logger.warning(f"[generate] Failed to update pending slides: {e}")

                            # V2 slides: generate images for each content item with image_prompt
                            if enable_image and new_v2:
                                from media_generation import generate_image
                                for sv2 in new_v2:
                                    for item in sv2.content:
                                        if item.image_prompt and not item.image_url:
                                            try:
                                                image_url = await generate_image(item.image_prompt)
                                                item.image_url = image_url
                                            except Exception as e:
                                                logger.warning(f"V2 image gen failed for scene {outline.id}: {e}")

                            # V2 quiz/exercise data
                            quiz_result_v2 = result.get("quiz_data")
                            if outline.type == "quiz" and quiz_result_v2:
                                quiz_result_v2["scene_id"] = outline.id
                                quiz_data.append(quiz_result_v2)
                                pending_quiz_data_for_db.append(quiz_result_v2)
                                # Push newly generated quiz to pending list for frontend polling
                                try:
                                    from db import update_course_generation_status
                                    update_course_generation_status(
                                        course_id=session_id,
                                        pending_quiz_data=pending_quiz_data_for_db.copy()
                                    )
                                except Exception as e:
                                    logger.warning(f"[generate] Failed to update pending quiz data: {e}")
                            # V2 exercise data
                            exercise_result_v2 = result.get("exercise_data")
                            if outline.type == "exercise" and exercise_result_v2:
                                exercise_result_v2["scene_id"] = outline.id
                                exercise_data.append(exercise_result_v2)
                                pending_exercise_data_for_db.append(exercise_result_v2)
                                try:
                                    from db import update_course_generation_status
                                    update_course_generation_status(
                                        course_id=session_id,
                                        pending_exercise_data=pending_exercise_data_for_db.copy()
                                    )
                                except Exception as e:
                                    logger.warning(f"[generate] Failed to update pending exercise data: {e}")
                            # quiz/exercise: V1 fallback only when V2 missing data
                            if outline.type in ("quiz", "exercise"):
                                v1_needed = (outline.type == "quiz" and not quiz_result_v2) or (outline.type == "exercise" and not exercise_result_v2)
                                if v1_needed:
                                    result_v1 = await self._generate_scene_content(course_title, outline, i + 1)
                                    if outline.type == "quiz" and result_v1.get("quiz_data"):
                                        result_v1["quiz_data"]["scene_id"] = outline.id
                                        quiz_data.append(result_v1["quiz_data"])
                                        pending_quiz_data_for_db.append(result_v1["quiz_data"])
                                        # Push fallback quiz to pending list for frontend polling
                                        try:
                                            from db import update_course_generation_status
                                            update_course_generation_status(
                                                course_id=session_id,
                                                pending_quiz_data=pending_quiz_data_for_db.copy()
                                            )
                                        except Exception as e:
                                            logger.warning(f"[generate] Failed to update pending quiz data (fallback): {e}")
                                    if outline.type == "exercise" and result_v1.get("exercise_data"):
                                        result_v1["exercise_data"]["scene_id"] = outline.id
                                        exercise_data.append(result_v1["exercise_data"])
                                        pending_exercise_data_for_db.append(result_v1["exercise_data"])
                                        # Push fallback exercise to pending list for frontend polling
                                        try:
                                            from db import update_course_generation_status
                                            update_course_generation_status(
                                                course_id=session_id,
                                                pending_exercise_data=pending_exercise_data_for_db.copy()
                                            )
                                        except Exception as e:
                                            logger.warning(f"[generate] Failed to update pending exercise data (fallback): {e}")
                            # interactive: attach interactive_data
                            if outline.type == "interactive":
                                idata = result.get("interactive_data")
                                if idata:
                                    idata["scene_id"] = outline.id
                                    interactive_data.append(idata)
                            # code: attach code_data for interactive editor
                            if outline.type == "code":
                                cd = result.get("code_data")
                                if cd:
                                    cd["scene_id"] = outline.id
                                    code_data.append(cd)
                            # whiteboard: attach description and actions to outline for frontend
                            if outline.type == "whiteboard":
                                outline.whiteboard_description = result.get("whiteboard_description", outline.description)
                                outline.speech = result.get("speech", f"现在我们来学习{outline.title}的内容。")
                                wb_actions = result.get("whiteboard_actions", [])
                                if wb_actions:
                                    outline.whiteboard_actions = wb_actions
                            if new_v2:
                                yield {
                                    "type": "slide_content",
                                    "progress": 55 + int(((i + 1 - (first_batch_done_index + 1)) / max(total - (first_batch_done_index + 1), 1)) * 17),
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
                                result["quiz_data"]["scene_id"] = outline.id
                                quiz_data.append(result["quiz_data"])
                                pending_quiz_data_for_db.append(result["quiz_data"])
                                try:
                                    from db import update_course_generation_status
                                    update_course_generation_status(
                                        course_id=session_id,
                                        pending_quiz_data=pending_quiz_data_for_db.copy()
                                    )
                                except Exception as e:
                                    logger.warning(f"[generate] Failed to update pending quiz data (V1): {e}")
                            if result.get("exercise_data"):
                                result["exercise_data"]["scene_id"] = outline.id
                                exercise_data.append(result["exercise_data"])
                                pending_exercise_data_for_db.append(result["exercise_data"])
                                try:
                                    from db import update_course_generation_status
                                    update_course_generation_status(
                                        course_id=session_id,
                                        pending_exercise_data=pending_exercise_data_for_db.copy()
                                    )
                                except Exception as e:
                                    logger.warning(f"[generate] Failed to update pending exercise data (V1): {e}")

                            yield {
                                "type": "slide_content",
                                "progress": 55 + int(((i + 1 - (first_batch_done_index + 1)) / max(total - (first_batch_done_index + 1), 1)) * 17),
                                "data": {
                                    "slide_id": slide.id,
                                    "title": slide.title,
                                    "speech_preview": slide.speech[:60] + "..." if len(slide.speech) > 60 else slide.speech,
                                    "scene_type": outline.type,
                                }
                            }
                    except Exception as e:
                        logger.exception(f"[generate] 4b FAILED at outline[{i}] type={outline.type}: {e}")
                        # 容错：单个outline失败不中断整体生成，继续下一个
                        continue

                # --- 4b完成：更新生成进度 ---
                try:
                    from db import update_course_generation_status
                    update_course_generation_status(
                        course_id=session_id,
                        generated_count=total,
                        pending_slides_v2=pending_slides_v2_for_db.copy() if pending_slides_v2_for_db else [],
                        pending_quiz_data=pending_quiz_data_for_db.copy() if pending_quiz_data_for_db else [],
                        pending_exercise_data=pending_exercise_data_for_db.copy() if pending_exercise_data_for_db else []
                    )
                except Exception as e:
                    logger.warning(f"[generate] Failed to update generation status after 4b: {e}")

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
                    # Also generate images for V2 slides that missed inline generation
                    if slides_v2:
                        v2_img_events = await self._generate_images_v2(slides_v2)
                        for evt in v2_img_events:
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

                # ---- Phase 7: 视频生成（并发生成 + SSE 心跳）----
                if enable_video and slides_v2:
                    # 收集所有待生成视频的任务
                    video_tasks: list[dict[str, Any]] = []
                    for sv2 in slides_v2:
                        for item in sv2.content:
                            prompt = item.video_prompt or item.image_prompt
                            if not prompt:
                                continue
                            video_tasks.append({"slide": sv2, "item": item, "prompt": prompt})

                    if video_tasks:
                        yield {
                            "type": "status",
                            "progress": 89,
                            "data": {"msg": f"正在并发生成 {len(video_tasks)} 个教学视频（耗时较长，请耐心等待）..."}
                        }

                        async def _gen_one(task: dict) -> dict[str, Any]:
                            try:
                                from media_generation import generate_video
                                url = await generate_video(prompt=task["prompt"])
                                task["item"].video_url = url
                                logger.info(f"[video] generated for slide '{task['slide'].title[:30]}': {url[:80]}")
                                return {"ok": True, "title": task["slide"].title[:30], "url": url}
                            except Exception as e:
                                logger.warning(f"[video] generation failed for slide '{task['slide'].title[:30]}': {e}")
                                return {"ok": False, "title": task["slide"].title[:30], "error": str(e)}

                        coros = [_gen_one(t) for t in video_tasks]
                        completed = 0
                        failed = 0
                        pending = set(asyncio.ensure_future(c) for c in coros)

                        while pending:
                            done, pending = await asyncio.wait(
                                pending, timeout=15,
                                return_when=asyncio.FIRST_COMPLETED
                            )
                            for fut in done:
                                result = fut.result()
                                if result["ok"]:
                                    completed += 1
                                else:
                                    failed += 1
                            # 向 SSE 前端回传进度（同时作为心跳防止超时断开）
                            remaining = len(pending)
                            yield {
                                "type": "status",
                                "progress": 90,
                                "data": {
                                    "msg": f"视频生成中... 已完成 {completed}/{len(video_tasks)}"
                                           + (f"，失败 {failed}" if failed else "")
                                           + (f"，剩余 {remaining} 个" if remaining else "")
                                }
                            }
                        yield {
                            "type": "status",
                            "progress": 94,
                            "data": {"msg": f"视频生成完成（成功 {completed} 个" + (f"，失败 {failed} 个" if failed else "") + "）"}
                        }
                    else:
                        yield {
                            "type": "status",
                            "progress": 89,
                            "data": {"msg": "视频生成完成（无可用场景）"}
                        }
                else:
                    yield {
                        "type": "status",
                        "progress": 89,
                        "data": {"msg": "跳过视频生成"}
                    }

                # ---- Phase 8: 构建最终数据 ----
                teacher = TeacherInfo(
                    name=self.config.teacher_name,
                    avatar=self.config.teacher_avatar,
                    role="课程导师",
                    voice_id=self.config.voice_id,
                    profession=self.config.teacher_profession,
                    personality=self.config.teacher_personality,
                    teaching_style=self.config.teacher_teaching_style,
                    icon=self.config.teacher_icon,
                    system_prompt=self.config.teacher_system_prompt,
                    greeting=self.config.teacher_greeting,
                )

                course_data = CourseData(
                    courseId=session_id,  # 使用session_id作为courseId以便前端轮询
                    title=course_title,
                    outlines=outlines,
                    slides=slides,
                    slides_v2=slides_v2,
                    teacher=teacher,
                    agent_team=agent_team,
                    quiz_data=quiz_data,
                    exercise_data=exercise_data,
                    interactive_data=interactive_data,
                    code_data=code_data,
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

                # --- 完成：更新数据库状态为complete ---
                try:
                    from db import update_course_generation_status
                    update_course_generation_status(
                        course_id=session_id,
                        generated_count=total,
                        pending_slides_v2=[],
                        is_complete=1
                    )
                except Exception as e:
                    logger.warning(f"[generate] Failed to update generation status at done: {e}")

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
                    # Strip <think> reasoning tags that some models emit
                    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", result)
                    cleaned = cleaned.replace("</think>", "")
                    return cleaned.strip()
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

    async def _generate_outlines(self, requirement: str, requirement_analysis: dict | None = None) -> list[SceneOutline]:
        """用LLM生成课程大纲，智能分配场景类型，确保边学边练"""
        pdf_context = ""
        if self.config.enable_pdf_upload and getattr(self, '_pdf_text', ''):
            pdf_context = f"""
## 参考文档内容（请严格基于以下文档构建课程大纲，确保所有知识点和结构来源于此文档）

{self._pdf_text}
"""
        # 构建建议场景类型提示
        suggested_types_text = ""
        if requirement_analysis:
            suggested = requirement_analysis.get("suggested_scene_types", [])
            if suggested:
                type_names = {
                    "slide": "幻灯片讲解", "quiz": "课堂测验", "exercise": "互动练习",
                    "interactive": "交互模拟", "pbl": "项目探究", "diagram": "图表展示",
                    "code": "编程实践", "video": "视频素材", "whiteboard": "白板绘图"
                }
                names = [type_names.get(t, t) for t in suggested]
                suggested_types_text = f"\n## 建议重点使用的场景类型（根据需求分析）\n{', '.join(names)}\n"

        raw = await self._call_llm_with_retry(
            "你是一位课程设计专家，严格按JSON格式输出。",
            build_prompt(
                "outline_generation_v3",
                requirement=requirement,
                course_type="general",
                pdf_text=pdf_context,
                suggested_scene_types=suggested_types_text,
            ),
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

        # ---- 后处理：确保场景类型分布合理（边学边练）----
        outlines = self._ensure_scene_diversity(outlines)

        return outlines

    def _ensure_scene_diversity(self, outlines: list[SceneOutline]) -> list[SceneOutline]:
        """
        确保场景类型分布合理：
        1. 互动型场景（quiz/exercise/interactive/pbl/code）不能连续出现
        2. 讲授型场景（slide/diagram/video/whiteboard）连续不超过3个
        3. 边学边练：整体上讲授与互动交替
        """
        if len(outlines) < 3:
            return outlines

        interactive_types = {"quiz", "exercise", "interactive", "pbl", "code"}
        lecture_types = {"slide", "diagram", "video", "whiteboard"}

        # 第一轮：修复连续的非slide场景（互动型不能连续）
        for i in range(1, len(outlines)):
            if outlines[i].type in interactive_types and outlines[i - 1].type in interactive_types:
                prev_type = outlines[i - 1].type
                curr_type = outlines[i].type
                logger.info(f"[diversity] 修复连续互动场景 at {i}: {prev_type} -> {curr_type}，将后者改为slide")
                outlines[i].type = "slide"

        # 第二轮：修复超过3个连续的讲授型场景（边学边练，不能一直讲）
        lecture_streak = 0
        for i in range(len(outlines)):
            if outlines[i].type in lecture_types:
                lecture_streak += 1
                if lecture_streak >= 3:
                    # 根据位置和内容特点选择最合适的互动类型
                    if i == len(outlines) - 1:
                        # 最后一个场景，用exercise做总结
                        outlines[i].type = "exercise"
                    elif "代码" in outlines[i].title or "编程" in outlines[i].title or "函数" in outlines[i].title:
                        outlines[i].type = "code"
                    elif "测试" in outlines[i].title or "检验" in outlines[i].title or "复习" in outlines[i].title:
                        outlines[i].type = "quiz"
                    elif i > len(outlines) // 2:
                        # 后半段用综合练习
                        outlines[i].type = "exercise"
                    else:
                        outlines[i].type = "quiz"
                    lecture_streak = 0
                    logger.info(f"[diversity] 修复过长讲授序列 at {i}，转为{outlines[i].type}")
            else:
                lecture_streak = 0

        # 第三轮：确保整体有合理的互动密度（至少每3个场景有1个互动）
        for i in range(len(outlines)):
            window = outlines[max(0, i - 2):i + 1]
            if len(window) == 3 and all(o.type in lecture_types for o in window):
                # 将中间的一个改为quiz
                mid_idx = i - 1
                outlines[mid_idx].type = "quiz"
                logger.info(f"[diversity] 增加互动密度 at {mid_idx}，转为quiz")

        # 重新编号
        for i, o in enumerate(outlines):
            o.id = i + 1

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
        pdf_context = ""
        if self.config.enable_pdf_upload and getattr(self, '_pdf_text', ''):
            pdf_context = f"""
## 参考文档内容（请严格基于以下文档构建，确保内容准确）

{self._pdf_text}
"""

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
                    pdf_text=pdf_context,
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
        prev_outline_title: str = "",
        next_outline_title: str = "",
        skip_web_search: bool = False,
    ) -> dict[str, Any]:
        """用LLM生成V2格式幻灯片内容（结构化布局）—— 强容错版本"""
        pdf_context = ""
        if self.config.enable_pdf_upload and getattr(self, '_pdf_text', ''):
            pdf_context = f"""
## 参考文档内容（请严格基于以下文档构建幻灯片，确保知识点准确来源于文档）

{self._pdf_text}
"""

        web_search_context = ""
        if self.config.enable_web_search and not skip_web_search:
            try:
                from app.services.teacher.web_search import search_minimax, search_web, format_as_context
                query = f"{outline.title} {', '.join(outline.key_points) if outline.key_points else ''}"
                logger.info(f"[web_search] searching for outline: {query[:80]}")

                # 优先 MiniMax MCP 搜索
                resp = await search_minimax(query)
                if resp and (resp.results or resp.answer):
                    web_search_context = format_as_context(resp)
                    logger.info(f"[web_search] MiniMax got {resp.source_count} results for: {outline.title}")
                else:
                    # Fallback 到 Tavily
                    results = await search_web(query)
                    web_search_context = format_as_context(results)
                    logger.info(f"[web_search] Tavily got {results.source_count} results for: {outline.title}")
            except Exception as e:
                logger.warning(f"[web_search] failed for outline {outline.title}: {e}")

        # --- Quiz场景：生成测验题目 ---
        if outline.type == "quiz":
            logger.info(f"[_generate_scene_content_v2] generating quiz for outline: {outline.title}")
            try:
                quiz_prompt = build_prompt(
                    "quiz_content",
                    course_title=course_title,
                    outline_title=outline.title,
                    outline_description=outline.description,
                    key_points=", ".join(outline.key_points) if outline.key_points else outline.title,
                    web_search_context=web_search_context,
                    pdf_text=pdf_context,
                    scene_id=outline.id,
                )
                quiz_raw = await self._call_llm_with_retry(
                    "你是一位测验出题专家，严格按JSON格式输出。",
                    quiz_prompt,
                    temperature=0.5,
                )
                quiz_data = self._extract_json(quiz_raw)
                logger.info(f"[_generate_scene_content_v2] quiz generated with {len(quiz_data.get('questions', []))} questions for outline: {outline.title}")
                # Return empty slides_v2 (quiz scenes don't need slides) and quiz_data
                return {"slides_v2": [], "quiz_data": quiz_data}
            except Exception as e:
                logger.error(f"[_generate_scene_content_v2] quiz generation failed for {outline.title}: {e}")
                return {"slides_v2": [], "quiz_data": None}

        # --- Exercise场景：生成练习内容（V2） ---
        if outline.type == "exercise":
            logger.info(f"[_generate_scene_content_v2] generating exercise for outline: {outline.title}")
            try:
                exercise_prompt = build_prompt(
                    "exercise_scene_content_v2",
                    course_title=course_title,
                    outline_title=outline.title,
                    outline_description=outline.description,
                    key_points=", ".join(outline.key_points) if outline.key_points else outline.title,
                )
                exercise_raw = await self._call_llm_with_retry(
                    "你是一位编程教育练习设计专家，严格按JSON格式输出。",
                    exercise_prompt,
                    temperature=0.5,
                )
                exercise_data = self._extract_json(exercise_raw)
                logger.info(f"[_generate_scene_content_v2] exercise generated for: {outline.title}")

                # Parse slides_v2 if present
                slides_v2_batch: list[SlideV2] = []
                raw_slides = exercise_data.get("slides_v2", [])
                if isinstance(raw_slides, list):
                    for idx, slide_data in enumerate(raw_slides):
                        try:
                            if not isinstance(slide_data, dict):
                                continue
                            content_items: list[SlideContentItemV2] = []
                            for item_data in slide_data.get("content", []):
                                if not isinstance(item_data, dict):
                                    continue
                                content_items.append(SlideContentItemV2(
                                    sub_title=item_data.get("sub_title") or item_data.get("subTitle") or "",
                                    bullets=[str(b).strip() for b in item_data.get("bullets", []) if b and str(b).strip()],
                                    narration=str(item_data.get("narration") or "").strip(),
                                    text=str(item_data.get("text") or "").strip(),
                                    icon=item_data.get("icon", "book"),
                                    color_theme=item_data.get("color_theme") or item_data.get("colorTheme") or "blue",
                                ))
                            slides_v2_batch.append(SlideV2(
                                layout_type=slide_data.get("layout_type") or slide_data.get("layoutType") or "two-column",
                                title=slide_data.get("title") or outline.title,
                                content=content_items,
                            ))
                        except Exception as e:
                            logger.warning(f"[_generate_scene_content_v2] exercise slides[{idx}] parse error: {e}")
                            continue

                return {
                    "slides_v2": slides_v2_batch,
                    "exercise_data": exercise_data.get("exercise_data", {}),
                    "speech": exercise_data.get("speech", f"现在我们来完成关于{outline.title}的练习。"),
                }
            except Exception as e:
                logger.error(f"[_generate_scene_content_v2] exercise generation failed for {outline.title}: {e}")
                return {
                    "slides_v2": [],
                    "exercise_data": {
                        "title": outline.title,
                        "exercises": [
                            {
                                "type": "choice",
                                "instruction": f"关于{outline.title}，以下哪项描述是正确的？",
                                "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
                                "correct_answer": 0,
                                "explanation": outline.description or "",
                            }
                        ],
                    },
                    "speech": f"现在我们来完成关于{outline.title}的练习。",
                }

        # --- Interactive场景：生成交互式模拟内容 ---
        if outline.type == "interactive":
            logger.info(f"[_generate_scene_content_v2] generating interactive scene for outline: {outline.title}")
            try:
                # 根据标题推断 widget 类型
                title_lower = outline.title.lower()
                desc_lower = outline.description.lower() if outline.description else ""
                combined = title_lower + " " + desc_lower

                if any(k in combined for k in ["redis", "cli", "命令行", "终端", "terminal", "shell", "bash", "cmd", "powershell", "git"]):
                    widget_type = "terminal"
                    prompt_id = "interactive_terminal"
                elif any(k in combined for k in ["图表", "流程", "关系", "diagram", "mermaid", "flow", "uml", "类图", "时序"]):
                    widget_type = "diagram"
                    prompt_id = "interactive_diagram"
                elif any(k in combined for k in ["游戏", "配对", "记忆", "game", "quiz", "闯关", "挑战"]):
                    widget_type = "game"
                    prompt_id = "interactive_game"
                elif any(k in combined for k in ["可视化", "动画", "排序", "数据结构", "栈", "队列", "链表", "树", "二叉树", "算法", "algorithm", "visualization", "visualize"]):
                    widget_type = "code_visualizer"
                    prompt_id = "interactive_simulation"
                elif any(k in combined for k in ["模拟", "实验", "物理", "simulation", "simulate"]):
                    widget_type = "simulation"
                    prompt_id = "interactive_simulation"
                else:
                    widget_type = "simulation"
                    prompt_id = "interactive_simulation"

                interactive_prompt = build_prompt(
                    prompt_id,
                    course_title=course_title,
                    outline_title=outline.title,
                    outline_description=outline.description,
                    key_points=", ".join(outline.key_points) if outline.key_points else outline.title,
                )
                interactive_raw = await self._call_llm_with_retry(
                    "你是一位交互式学习内容设计专家，严格按JSON格式输出。",
                    interactive_prompt,
                    temperature=0.6,
                )
                interactive_data = self._extract_json(interactive_raw)
                logger.info(f"[_generate_scene_content_v2] interactive scene generated with widget_type={widget_type} for: {outline.title}")

                # Build interactive_data object
                interactive_result = {
                    "id": outline.id,
                    "scene_id": outline.id,
                    "title": interactive_data.get("title", outline.title),
                    "widget_type": interactive_data.get("widget_type", widget_type),
                    "html_content": interactive_data.get("html", ""),
                    "config": interactive_data.get("config", {}),
                    "speech": interactive_data.get("speech", f"现在我们来体验{outline.title}的交互模拟。"),
                }

                return {
                    "slides_v2": [],
                    "interactive_data": interactive_result,
                    "speech": interactive_result["speech"],
                }
            except Exception as e:
                logger.error(f"[_generate_scene_content_v2] interactive generation failed for {outline.title}: {e}")
                # Fallback: build a built-in terminal if it's a CLI-related topic
                title_lower = outline.title.lower()
                desc_lower = outline.description.lower() if outline.description else ""
                if any(k in title_lower + " " + desc_lower for k in ["redis", "cli", "命令行", "终端"]):
                    return {
                        "slides_v2": [],
                        "interactive_data": {
                            "id": outline.id,
                            "scene_id": outline.id,
                            "title": outline.title,
                            "widget_type": "terminal",
                            "html_content": "",
                            "config": {"type": "terminal"},
                            "speech": f"现在我们来体验{outline.title}的交互模拟。",
                        },
                        "speech": f"现在我们来体验{outline.title}的交互模拟。",
                    }
                return {
                    "slides_v2": [],
                    "interactive_data": None,
                    "speech": f"现在我们来学习{outline.title}的内容。",
                }

        # --- Code场景：生成交互式代码编辑器内容 ---
        if outline.type == "code":
            logger.info(f"[_generate_scene_content_v2] generating code scene for outline: {outline.title}")
            try:
                code_prompt = build_prompt(
                    "code_scene_content",
                    course_title=course_title,
                    outline_title=outline.title,
                    outline_description=outline.description,
                    key_points=", ".join(outline.key_points) if outline.key_points else outline.title,
                )
                code_raw = await self._call_llm_with_retry(
                    "你是一位编程教学专家，严格按JSON格式输出。",
                    code_prompt,
                    temperature=0.5,
                )
                code_data = self._extract_json(code_raw)
                logger.info(f"[_generate_scene_content_v2] code scene generated for: {outline.title}")

                # Parse slides_v2 if present
                slides_v2_batch: list[SlideV2] = []
                raw_slides = code_data.get("slides_v2", [])
                if isinstance(raw_slides, list):
                    for idx, slide_data in enumerate(raw_slides):
                        try:
                            if not isinstance(slide_data, dict):
                                continue
                            content_items: list[SlideContentItemV2] = []
                            for item_data in slide_data.get("content", []):
                                if not isinstance(item_data, dict):
                                    continue
                                content_items.append(SlideContentItemV2(
                                    sub_title=item_data.get("sub_title") or item_data.get("subTitle") or "",
                                    bullets=[str(b).strip() for b in item_data.get("bullets", []) if b and str(b).strip()],
                                    narration=str(item_data.get("narration") or "").strip(),
                                    text=str(item_data.get("text") or "").strip(),
                                    icon=item_data.get("icon", "book"),
                                    color_theme=item_data.get("color_theme") or item_data.get("colorTheme") or "blue",
                                ))
                            slides_v2_batch.append(SlideV2(
                                layout_type=slide_data.get("layout_type") or slide_data.get("layoutType") or "two-column",
                                title=slide_data.get("title") or outline.title,
                                content=content_items,
                            ))
                        except Exception as e:
                            logger.warning(f"[_generate_scene_content_v2] code scene slides[{idx}] parse error: {e}")
                            continue

                return {
                    "slides_v2": slides_v2_batch,
                    "code_data": code_data.get("code_data", {}),
                    "speech": code_data.get("speech", f"现在我们来学习{outline.title}的内容。"),
                }
            except Exception as e:
                logger.error(f"[_generate_scene_content_v2] code scene generation failed for {outline.title}: {e}")
                return {
                    "slides_v2": [],
                    "code_data": {
                        "language": "python",
                        "starter_code": "# TODO: 请在此编写代码\n",
                        "instruction": outline.description or f"请完成关于{outline.title}的编程练习",
                        "expected_output": "",
                        "hints": ["仔细阅读题目要求", "从简单的实现开始", "测试边界条件"],
                        "explanation": f"{outline.title}是编程学习中的重要概念。",
                    },
                    "speech": f"现在我们来学习{outline.title}的内容。",
                }

        # --- Whiteboard场景：生成绘图描述、语音和白板actions ---
        if outline.type == "whiteboard":
            logger.info(f"[_generate_scene_content_v2] generating whiteboard for outline: {outline.title}")
            try:
                wb_prompt = f"""你是一位教学绘图设计专家。请根据以下课程大纲，设计一个白板绘制方案。

课程主题：{course_title}
场景标题：{outline.title}
场景描述：{outline.description}
关键知识点：{", ".join(outline.key_points) if outline.key_points else outline.title}

白板尺寸: 宽1000 x 高562.5

要求：
1. 用自然语言详细描述要在白板上绘制的内容（包含具体图形、坐标、标注等）
2. 描述应包含绘制步骤（先画什么，再画什么）
3. 同时生成一段AI教师的语音讲解稿（200-300字），配合白板绘制过程
4. 【新增】直接输出白板绘图动作数组(actions)，每个action包含 type 和 params

可用动作类型：
- wb_draw_text: 写文字。params: {{content, x, y, fontSize(可选,默认20), color(可选,默认#333)}}
- wb_draw_shape: 几何图形。params: {{shape: "rectangle|circle|triangle", x, y, width, height, fillColor(可选), strokeColor(可选)}}
- wb_draw_svg: SVG矢量图。params: {{svg: "SVG字符串(不含<svg>外层标签)", x, y, width, height}}
- wb_draw_line: 线条/箭头。params: {{startX, startY, endX, endY, color(可选), width(可选), style(可选, "solid|dashed"), points(可选, ["","arrow"])}}
- wb_draw_code: 代码块。params: {{language, code, x, y, width(可选,默认500), height(可选,默认300)}}

布局约束：
- 元素之间保持 ≥ 30px 间距，严禁重叠
- 内容从左上角开始排列，合理分布
- 坐标取整数

以JSON格式输出：
{{
  "whiteboard_description": "详细的白板绘制描述...",
  "speech": "AI教师语音讲解稿...",
  "actions": [
    {{"type": "wb_draw_text", "params": {{"content": "标题", "x": 50, "y": 50, "fontSize": 24}}}},
    {{"type": "wb_draw_shape", "params": {{"shape": "rectangle", "x": 100, "y": 100, "width": 200, "height": 150}}}}
  ]
}}

只输出JSON，不要其他文字。"""
                wb_raw = await self._call_llm_with_retry(
                    "你是一位教学绘图设计专家，严格按JSON格式输出。",
                    wb_prompt,
                    temperature=0.7,
                )
                wb_data = self._extract_json(wb_raw)
                # Validate actions
                raw_actions = wb_data.get("actions", [])
                valid_actions = []
                valid_types = {
                    "wb_draw_text", "wb_draw_shape", "wb_draw_svg", "wb_draw_latex",
                    "wb_draw_chart", "wb_draw_table", "wb_draw_line", "wb_draw_code",
                    "wb_clear", "wb_delete", "wb_open", "wb_close",
                }
                for act in raw_actions:
                    if isinstance(act, dict):
                        t = act.get("type") or act.get("name")
                        if t in valid_types:
                            params = act.get("params") or act.get("parameters") or {}
                            if isinstance(params, dict):
                                valid_actions.append({"type": t, "params": params})

                return {
                    "slides_v2": [],
                    "whiteboard_description": wb_data.get("whiteboard_description", outline.description),
                    "whiteboard_actions": valid_actions,
                    "speech": wb_data.get("speech", f"现在我们来学习{outline.title}的内容。"),
                }
            except Exception as e:
                logger.error(f"[_generate_scene_content_v2] whiteboard generation failed for {outline.title}: {e}")
                return {
                    "slides_v2": [],
                    "whiteboard_description": outline.description,
                    "whiteboard_actions": [],
                    "speech": f"现在我们来学习{outline.title}的内容。",
                }

        # --- 混合策略：以指定概率使用 MiniMax 生成精美 OpenMAIC 格式 ---
        if (outline.type == "slide"
            and getattr(self.config, 'enable_minimax_ppt', False)):
            import random
            if random.random() < getattr(self.config, 'minimax_ppt_ratio', 0.7):
                try:
                    from app.services.ppt import get_ppt_provider, PPTGenerationRequest

                    # 构造 content items
                    content_items: list[dict[str, Any]] = []
                    key_points = outline.key_points or []
                    if key_points:
                        for i, point in enumerate(key_points):
                            content_items.append({
                                "sub_title": f"要点 {i+1}",
                                "text": point,
                                "icon": "star",
                                "color_theme": ["blue", "yellow", "green", "purple", "orange"][i % 5],
                            })
                    elif outline.description:
                        content_items.append({
                            "sub_title": outline.title,
                            "text": outline.description,
                            "icon": "book",
                            "color_theme": "blue",
                        })

                    provider = get_ppt_provider()
                    design_styles = ["modern", "elegant", "minimal", "bold", "classic"]
                    request = PPTGenerationRequest(
                        course_title=course_title,
                        scene_title=outline.title,
                        scene_id=str(outline.id),
                        scene_type="slide",
                        content=content_items,
                        design_style=design_styles[slide_index % len(design_styles)],
                    )
                    result = await provider.generate(request)
                    if result.success and result.slide:
                        slide_dict = result.slide
                        # 确保 scene_id 用于前端匹配
                        slide_dict["scene_id"] = outline.id
                        slide_v2 = SlideV2(
                            layout_type=slide_dict.get("layoutType", slide_dict.get("layout_type", "two-column")),
                            title=slide_dict.get("title", outline.title),
                            content=[],  # OpenMAIC 格式不依赖 content
                            scene_id=outline.id,
                            elements=slide_dict.get("elements", []),
                            viewportSize=slide_dict.get("viewportSize"),
                            viewportRatio=slide_dict.get("viewportRatio"),
                            background=slide_dict.get("background"),
                            theme=slide_dict.get("theme"),
                            actions=slide_dict.get("actions", []),
                            id=slide_dict.get("id"),
                        )
                        logger.info(
                            f"[_generate_scene_content_v2] MiniMax PPT generated for '{outline.title}' "
                            f"({len(slide_dict.get('elements', []))} elements)"
                        )
                        return {"slides_v2": [slide_v2]}
                except Exception as e:
                    logger.warning(
                        f"[_generate_scene_content_v2] MiniMax PPT 生成失败，回退到通用生成: {e}"
                    )
                    # 继续走下面的通用生成逻辑

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
                    web_search_context=web_search_context,
                    pdf_text=pdf_context,
                    prev_outline_title=prev_outline_title or "（本课程第一节）",
                    next_outline_title=next_outline_title or "（本课程最后一节）",
                    available_layouts=self._layout_descriptions,
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
                layout_type = slide_data.get("layoutType") or slide_data.get("layout_type") or ""

                # diagram 场景强制使用适合图表的布局
                if outline.type == "diagram" and layout_type not in {"info-graphic", "timeline-steps", "stair-step"}:
                    logger.info(f"[_generate_scene_content_v2] diagram scene forcing layout from '{layout_type}' to 'info-graphic'")
                    layout_type = "info-graphic"

                # 校验 layout_type 合法性（根据用户选项过滤后的布局池）
                if layout_type not in self._active_layouts:
                    # 课程级轮询池：优先使用本课程尚未出现过的布局
                    import random
                    if not self._layout_pool:
                        # 池子耗尽，重新填充并 shuffle
                        self._layout_pool = list(self._active_layouts)
                        random.shuffle(self._layout_pool)
                    layout_type = self._layout_pool.pop()
                    logger.info(f"[_generate_scene_content_v2] fallback layout chosen: {layout_type} (pool remaining: {len(self._layout_pool)})")
                self._used_layouts.add(layout_type)

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

                        # --- Extract bullets array ---
                        bullets_raw = item_data.get("bullets", [])
                        if not isinstance(bullets_raw, list):
                            bullets_raw = []
                        bullets = [str(b).strip() for b in bullets_raw if b and str(b).strip()]

                        # --- Extract narration for TTS ---
                        narration = str(item_data.get("narration") or "").strip()

                        # --- Fallback text (backward compat) ---
                        text_raw = str(item_data.get("text") or "").strip()

                        # --- Auto-parse bullets from text if bullets is empty ---
                        if not bullets and text_raw:
                            for line in text_raw.strip().split('\n'):
                                m = re.match(r'^[-*]\s+(.+)', line.strip())
                                if m:
                                    bullets.append(m.group(1).strip())
                            # If still no bullets, treat first 200 chars as single bullet
                            if not bullets and text_raw:
                                bullets = [text_raw[:200]]

                        content_item = SlideContentItemV2(
                            sub_title=item_data.get("subTitle") or item_data.get("sub_title") or "",
                            bullets=bullets,
                            narration=narration,
                            text=text_raw,
                            icon=icon,
                            color_theme=color_theme,
                            code_snippet=item_data.get("codeSnippet") or "",
                            image_url=item_data.get("imageUrl") or item_data.get("image_url") or "",
                            image_prompt=item_data.get("image_prompt") or item_data.get("imagePrompt") or "",
                            video_url=item_data.get("videoUrl") or item_data.get("video_url") or None,
                            video_prompt=item_data.get("video_prompt") or item_data.get("videoPrompt") or None,
                        )
                        content_items.append(content_item)
                    except Exception as e:
                        logger.warning(f"[_generate_scene_content_v2] slides[{idx}].content[{cidx}] 解析异常: {e}，跳过该卡片")
                        continue

                # --- 关键修复：确保每个 slide 都有文字内容 ---
                if not content_items:
                    # LLM 生成了空 content，自动从 outline 填充 fallback
                    logger.warning(f"[_generate_scene_content_v2] slides[{idx}] content 为空，自动填充 fallback 文字")
                    fallback_bullets = []
                    if outline.key_points:
                        fallback_bullets = [str(k).strip() for k in outline.key_points if str(k).strip()]
                    elif outline.description:
                        fallback_bullets = [str(outline.description).strip()[:200]]
                    else:
                        fallback_bullets = [f"本节介绍{outline.title}的核心概念"]
                    content_items.append(SlideContentItemV2(
                        sub_title="核心要点",
                        bullets=fallback_bullets,
                        narration=f"同学们好，本节我们来学习{outline.title}。{outline.description or ''}"[:400],
                        text=outline.description or f"本节介绍{outline.title}的核心概念",
                        icon="book",
                        color_theme="blue",
                    ))
                else:
                    # 检查每个 content item 是否有文字，空的自动填充
                    for cii, ci in enumerate(content_items):
                        if not ci.bullets and not ci.text:
                            logger.warning(f"[_generate_scene_content_v2] slides[{idx}].content[{cii}] bullets和text均为空，自动填充")
                            ci.bullets = [f"关于{outline.title}的重要知识点"]
                            ci.text = f"本节介绍{outline.title}的核心概念"

                # Extract teacher_actions (whiteboard drawing actions)
                teacher_actions: list[TeacherAction] = []
                raw_actions = slide_data.get("teacherActions") or []
                if isinstance(raw_actions, list):
                    for act in raw_actions:
                        if isinstance(act, dict):
                            teacher_actions.append(TeacherAction(
                                type=act.get("type", ""),
                                params=act.get("params") or {},
                            ))

                slide_v2 = SlideV2(
                    layout_type=layout_type,
                    title=slide_title,
                    content=content_items,
                    teacher_actions=teacher_actions,
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
        """V2格式降级幻灯片 —— 使用多样化布局和颜色，避免千篇一律"""
        # diagram 场景使用适合图表展示的布局
        if outline.type == "diagram":
            layouts = ["info-graphic", "timeline-steps", "stair-step"]
        else:
            layouts = [
                "grid-cards", "header-content", "timeline-steps",
                "comparison", "three-column-cards", "hero-center",
                "edu-definition", "edu-keypoints", "edu-example"
            ]
        colors = ["blue", "yellow", "green", "purple", "orange"]
        icons = ["book", "lightbulb", "code", "check", "star"]
        # 基于 outline.id 的哈希轮换，确保不同 outline 有不同的视觉风格
        h = hash(outline.id) if outline.id else hash(outline.title)
        layout = layouts[abs(h) % len(layouts)]
        color = colors[abs(h >> 2) % len(colors)]
        icon = icons[abs(h >> 4) % len(icons)]
        return SlideV2(
            layout_type=layout,
            title=outline.title,
            content=[
                SlideContentItemV2(
                    sub_title="概述",
                    bullets=[f"本节将介绍{outline.title}的相关概念和应用"],
                    narration=f"同学们好，本节我们来学习{outline.title}的相关内容。",
                    text=f"本节将介绍{outline.title}的相关概念和应用",
                    icon=icon,
                    color_theme=color,
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
            # 根据课程标题推断最合适的默认编程教师
            defaultProfession = "全栈工程师"
            defaultName = "王浩宇"
            defaultPersona = "资深全栈工程师，拥有丰富的编程教学经验，擅长多技术栈的融会贯通"
            lowerTitle = course_title.lower() if course_title else ""
            if any(k in lowerTitle for k in ['python', '数据分析', '人工智能', '机器学习', '爬虫']):
                defaultProfession = "Python工程师"
                defaultName = "顾明远"
                defaultPersona = "资深Python工程师，擅长Python生态和数据科学，教学风格严谨而Pythonic"
            elif any(k in lowerTitle for k in ['java', 'spring', '后端', '企业级', 'android']):
                defaultProfession = "Java架构师"
                defaultName = "陈志强"
                defaultPersona = "资深Java架构师，精通企业级开发和分布式系统，注重架构思维和工程实践"
            elif any(k in lowerTitle for k in ['javascript', 'typescript', 'react', 'vue', '前端', 'html', 'css']):
                defaultProfession = "前端工程师"
                defaultName = "林小雅"
                defaultPersona = "资深前端工程师，精通现代前端技术栈，擅长用视觉化方式讲解抽象概念"
            elif any(k in lowerTitle for k in ['c++', 'c语言', '数据结构', '算法', '系统编程', '嵌入式']):
                defaultProfession = "C++系统工程师"
                defaultName = "赵铁柱"
                defaultPersona = "资深C++系统工程师，专注于底层开发和性能优化，崇尚对计算机原理的深入理解"
            return [{
                "id": "teacher_1",
                "name": defaultName,
                "role": "课程导师",
                "profession": defaultProfession,
                "persona": defaultPersona,
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
        """用LLM批改Quiz答案（增强版：支持单选/多选/简答，每道题都有AI个性化评价）"""
        import json
        total = len(questions)
        results: list[dict[str, Any]] = []
        total_score = 0
        total_points = 0

        # Build LLM prompt for batch grading
        grading_items = []
        for i, q in enumerate(questions):
            q_type = q.get("question_type", "single")
            points = q.get("points", 10)
            total_points += points

            # Find student's answer
            student_ans = None
            for sa in student_answers:
                if sa.get("question_index") == i or sa.get("index") == i:
                    student_ans = sa
                    break

            # Build answer description (兼容前端 _collectQuizAnswers 的数据格式)
            if q_type == "single":
                raw_val = student_ans.get("answer_value", -1) if student_ans else -1
                # Frontend sends answer_value as string (e.g. "0" or "")
                try:
                    user_val = int(raw_val) if raw_val != '' else -1
                except (ValueError, TypeError):
                    user_val = -1
                user_answer_text = q.get("options", [])[user_val] if user_val >= 0 and user_val < len(q.get("options", [])) else "(未作答)"
                correct_val = q.get("correct_answer", 0)
                correct_text = q.get("options", [])[correct_val] if correct_val >= 0 and correct_val < len(q.get("options", [])) else ""
                is_correct = (user_val == correct_val) and user_val >= 0
                score = points if is_correct else 0
            elif q_type == "multiple":
                user_vals = student_ans.get("answer_values", []) if student_ans else []
                correct_vals = q.get("correct_answers", [])
                user_set = set(user_vals)
                correct_set = set(correct_vals)
                is_correct = user_set == correct_set and len(user_set) == len(correct_set)
                score = points if is_correct else 0
                user_answer_text = ", ".join([q.get("options", [])[v] for v in user_vals if isinstance(v, int) and v < len(q.get("options", []))]) or "(未作答)"
                correct_text = ", ".join([q.get("options", [])[v] for v in correct_vals if isinstance(v, int) and v < len(q.get("options", []))])
            else:  # short_answer
                # Frontend sends answer_value (not "value") for short_answer
                user_answer_text = student_ans.get("answer_value", "") or student_ans.get("value", "") if student_ans else "(未作答)"
                correct_text = q.get("answer", "") or q.get("correct_answer", "")
                is_correct = False
                score = 0  # Will be determined by LLM

            total_score += score

            grading_items.append({
                "index": i,
                "type": q_type,
                "question": q.get("question", ""),
                "options": q.get("options", []),
                "user_answer": user_answer_text,
                "correct_answer": correct_text,
                "is_correct": is_correct,
                "score": score,
                "points": points,
                "key_points": q.get("key_points", []),
            })

        # Call LLM for personalized feedback on each question
        try:
            system_prompt = "你是一位耐心的教学专家。请对每道测验题给出详细、个性化的评价反馈。\n\n反馈要求：\n- 选择题：feedback 需 150-250 字，详细解释该选项为什么对/为什么错，关联相关知识点，指出常见的理解误区，并给出具体的学习建议。\n- 简答题：feedback 需 200-400 字，根据答案质量给出 0-100% 的评分，分析答案的优点和不足，指出遗漏的知识点，给出改进建议，并提供参考答案对比。\n- 所有 feedback 都用中文，语气鼓励但专业，避免空洞套话。\n\n请严格按JSON格式输出。"
            user_prompt = f"""请批改以下测验答案，对每道题给出个性化评价。

题目与答案：
{json.dumps(grading_items, ensure_ascii=False, indent=2)}

请返回如下JSON格式：
{{
  "results": [
    {{
      "question_index": 0,
      "is_correct": true/false,
      "score": 分数（0-满分）,
      "total_points": 满分,
      "feedback": "AI个性化评价，解释对错原因并给出学习建议",
      "correct_answer": "正确答案文本",
      "key_points_hit": ["学生答到的知识点"],
      "key_points_missed": ["学生遗漏的知识点"]
    }}
  ]
}}

注意：
- 选择题：is_correct 按规则判断，feedback 要解释为什么对/为什么错
- 简答题：请根据答案质量给出 0-100% 的评分，并给出详细反馈（优点、不足、改进建议）
- 所有 feedback 都用中文，语气鼓励但专业
"""
            raw = await self._call_llm_with_retry(system_prompt, user_prompt, temperature=0.4)
            parsed = self._extract_json(raw)
            llm_results = parsed.get("results", []) if isinstance(parsed, dict) else []
        except Exception as e:
            logger.warning(f"LLM grading failed, falling back to local: {e}")
            llm_results = []

        # Merge LLM feedback with rule-based scoring
        for i, item in enumerate(grading_items):
            llm_result = None
            for lr in llm_results:
                if lr.get("question_index") == i:
                    llm_result = lr
                    break

            if llm_result:
                # Use LLM score for short answer, keep rule-based for choices
                if item["type"] == "short_answer":
                    score = round(item["points"] * (llm_result.get("score", 50) / 100))
                    is_correct = score >= item["points"] * 0.6
                else:
                    score = item["score"]
                    is_correct = item["is_correct"]

                results.append({
                    "question_index": i,
                    "is_correct": is_correct,
                    "score": score,
                    "total_points": item["points"],
                    "feedback": llm_result.get("feedback", item.get("feedback", "")),
                    "correct_answer": llm_result.get("correct_answer", item["correct_answer"]),
                    "key_points_hit": llm_result.get("key_points_hit", []),
                    "key_points_missed": llm_result.get("key_points_missed", []),
                    "graded_by": "ai",
                })
            else:
                # Fallback to simple feedback (when LLM unavailable)
                if item["type"] == "short_answer":
                    fb = f"【AI评分服务暂不可用，以下为本地参考反馈】\n\n已收到你的答案。参考答案：{item['correct_answer']}。\n\n建议从以下几个方面对照检查自己的答案：\n1. 是否涵盖了题目要求的核心知识点？\n2. 表述是否清晰、逻辑是否连贯？\n3. 是否有具体的例子或论证支撑？\n\n联网后可获得AI的详细个性化评价。"
                    score = round(item["points"] * 0.5)
                    is_correct = False
                elif item["is_correct"]:
                    fb = f"回答正确！{item.get('explanation', '继续保持！')}"
                    score = item["points"]
                    is_correct = True
                else:
                    fb = f"回答错误。正确答案是：{item['correct_answer']}。建议回顾相关知识点，理解该概念的本质含义和应用场景。"
                    score = 0
                    is_correct = False

                results.append({
                    "question_index": i,
                    "is_correct": is_correct,
                    "score": score,
                    "total_points": item["points"],
                    "feedback": fb,
                    "correct_answer": item["correct_answer"],
                    "key_points_hit": [],
                    "key_points_missed": [],
                    "graded_by": "local",
                })

        # Recalculate totals (LLM may have changed short answer scores)
        total_score = sum(r["score"] for r in results)
        percentage = round(total_score / total_points * 100, 1) if total_points > 0 else 0

        return {
            "results": results,
            "total_score": total_score,
            "total_points": total_points,
            "percentage": percentage,
            "passed": percentage >= 60,
            "graded_count": len(results),
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

    async def _generate_images_v2(self, slides_v2: list[SlideV2]) -> list[dict]:
        """为V2幻灯片补生成配图（处理那些没有image_url但有image_prompt的content items）"""
        from media_generation import generate_image

        events: list[dict] = []
        total_items = 0
        processed = 0
        for sv2 in slides_v2:
            for item in sv2.content:
                if item.image_prompt and not item.image_url:
                    total_items += 1

        for sv2 in slides_v2:
            for item in sv2.content:
                if item.image_prompt and not item.image_url:
                    try:
                        image_url = await generate_image(item.image_prompt)
                        item.image_url = image_url
                        processed += 1
                        events.append({
                            "type": "image_progress",
                            "progress": 72 + int((processed / max(total_items, 1)) * 13),
                            "data": {"slide_title": sv2.title[:20], "image_url": image_url},
                        })
                    except Exception as e:
                        processed += 1
                        logger.warning(f"V2 image generation failed for slide '{sv2.title}': {e}")
                        events.append({
                            "type": "image_progress",
                            "progress": 72 + int((processed / max(total_items, 1)) * 13),
                            "data": {"slide_title": sv2.title[:20], "error": str(e)},
                        })
        return events

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


def get_course_generator() -> CourseGenerator:
    """获取课程生成器实例（每次新建，避免并发请求的竞态条件）"""
    return CourseGenerator()
