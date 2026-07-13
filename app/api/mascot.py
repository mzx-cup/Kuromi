# -*- coding: utf-8 -*-
"""
小星 AI 助手 API — SSE 流式对话 + 学习数据 + 签到

POST /api/mascot/chat/stream  — SSE 流式对话（上下文感知 + 主动推送）
GET  /api/mascot/stats/{user_id} — 快速学习统计
POST /api/mascot/checkin        — 每日签到
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from pydantic import BaseModel, Field

logger = logging.getLogger("starlearn.api.mascot")

router = APIRouter(prefix="/mascot", tags=["mascot"])


# =============================================================================
# 常量
# =============================================================================

# 小星的 System Prompt
MASCOT_SYSTEM_PROMPT = """你是「小星」🌟，星学平台(StarLearn)的 AI 学习伙伴。

你的性格设定:
- 温暖、耐心、鼓励型的陪伴式导师
- 像朋友一样聊天，但始终保持专业性
- 善于用 emoji 和轻松的语气让学习变得有趣
- 不直接给答案，而是用苏格拉底式提问引导学生思考

你的核心能力:
1. 回答学习问题（Python、算法、数据库、Web开发、AI等）
2. 解释概念、分析代码、调试错误
3. 提供学习建议和学习路径规划
4. 鼓励和激励学生保持学习动力
5. 推荐课程和学习资源
6. 根据学生的学习画像个性化回应

当前页面上下文: {page_context}
用户画像: {user_profile}
今日学习: {today_stats}

回复规则:
- 保持回复精炼但温暖，使用1-2个emoji
- 如果学生遇到困难，先共情，再提供具体帮助
- 如果学生学了很久，提醒休息
- 善于用比喻和类比来解释复杂概念
- 当需要导航到其他页面时，回复中包含 [navigate:目标页面]
- 如果需要表达情感，用 [expression:happy/surprised/thinking/encourage]

你能导航到的页面:
- AI问答 (学习问答页面)
- 课程中心 (课程列表页面)
- 学习数据 (数据看板)
- 个人中心 (个人中心页面)
- 代码工坊 (在线代码编辑器)
- 苏格拉底教学 (苏格拉底式对话学习)
"""


# =============================================================================
# 请求/响应模型
# =============================================================================

class MascotChatRequest(BaseModel):
    """小星对话请求"""
    message: str = Field(..., min_length=1, description="用户输入文本")
    student_id: str = Field(default="default", description="学生ID")
    page_context: str = Field(default="", description="当前页面上下文")
    conversation_history: list[dict] = Field(default_factory=list, description="对话历史")
    persona: str = Field(default="mascot", description="角色设定")
    model: str = Field(default="MiniMax-Text-01", description="AI 模型名称")
    temperature: float = Field(default=0.8, ge=0.0, le=2.0, description="生成温度")


class MascotCheckinRequest(BaseModel):
    """签到请求"""
    student_id: str = Field(..., description="学生ID")


# =============================================================================
# 工具函数
# =============================================================================

def _get_student_id_int(student_id: str) -> int:
    """将字符串 student_id 转为整数（用于数据库查询）"""
    try:
        return int(student_id)
    except (ValueError, TypeError):
        # 尝试用 hash 生成一个稳定的整数 ID
        return abs(hash(str(student_id))) % (10 ** 9)


def _build_today_stats(student_id: str) -> str:
    """Build today's stats using Repository abstraction."""
    try:
        from app.core.repository_factory import get_repository_for_user
        repo = get_repository_for_user(student_id, repository_type="learning")
        overview = repo.get_overview(student_id)
        # Sync call — wrap in async or use asyncio.run
        if asyncio.iscoroutine(overview):
            overview = asyncio.get_event_loop().run_until_complete(overview)
        total_minutes = overview.get("total_minutes", 0)
        streak = overview.get("current_streak", 0)
        return f"已学习 {total_minutes} 分钟，连续 {streak} 天"
    except Exception as e:
        logger.warning(f"[mascot] _build_today_stats 失败: {e}")
        return "暂无学习数据"


def _build_user_profile_text(student_id: str) -> str:
    """Build user profile text using Repository (memories from ChatRepository)."""
    try:
        from app.core.repository_factory import get_repository_for_user
        chat_repo = get_repository_for_user(student_id, repository_type="chat")
        memories = chat_repo.get_memories(student_id, limit=10)
        if asyncio.iscoroutine(memories):
            memories = asyncio.get_event_loop().run_until_complete(memories)
        if not memories:
            return "暂无用户记忆"
        lines = [f"- {m.get('content', m.get('text', ''))[:80]}" for m in memories[:5]]
        return "用户记忆摘要：\n" + "\n".join(lines)
    except Exception as e:
        logger.warning(f"[mascot] _build_user_profile_text 失败: {e}")
        return "暂无用户记忆"


# =============================================================================
# 端点
# =============================================================================

# Module-level singleton (mockable in tests)
_mascot_adapter = None


def _get_mascot_adapter():
    """Lazy-init the MascotEngineAdapter singleton.

    Kept as a separate function (instead of inlining the `global` assignment)
    so tests can monkeypatch ``_mascot_adapter`` directly without needing to
    mock the import path.
    """
    global _mascot_adapter
    if _mascot_adapter is None:
        from app.services.tutor_engine.mascot_adapter import MascotEngineAdapter
        _mascot_adapter = MascotEngineAdapter()
    return _mascot_adapter


@router.post("/chat/stream")
async def mascot_chat_stream(req: MascotChatRequest):
    """
    小星 SSE 流式对话 (通过 MascotEngineAdapter 路由)。

    事件类型:
      event: text_delta        data: {"content": "..."}
      event: command           data: {"tag": "navigate|expression|action", "content": "..."}
      event: link              data: {"title": "...", "url": "...", "type": "internal|external", "description": "..."}
      event: proactive_action  data: {"type": "...", "priority": int, "payload": {...}}
      event: action            data: {"type": "proactive", "title": "...", "content": "...", "action_label": "..."}
      event: done              data: {"full_text": "..."}
      event: error             data: {"message": "..."}
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    adapter = _get_mascot_adapter()

    async def event_stream():
        assistant_message = ""
        envelope = None

        try:
            envelope = await adapter.decide(req.student_id, req.message)
        except Exception as e:
            logger.error(f"[mascot] adapter.decide 失败: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"
            return

        # 1) Stream text — preserve existing text_delta semantics for backward compat.
        try:
            if envelope.answer_stream is not None:
                async for chunk in envelope.answer_stream:
                    # chunk may be a dict ({"type": "content_chunk", "content": "..."})
                    # or a plain string. Handle both.
                    if isinstance(chunk, dict):
                        content = chunk.get("content", "") or ""
                        if not content and chunk.get("type") == "done":
                            full_text = chunk.get("full_text")
                            if isinstance(full_text, str) and full_text:
                                assistant_message = full_text
                                yield f"event: text_delta\ndata: {json.dumps({'content': full_text}, ensure_ascii=False)}\n\n"
                            continue
                    else:
                        content = str(chunk)
                    if content:
                        assistant_message += content
                        yield f"event: text_delta\ndata: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
            elif envelope.answer_text:
                assistant_message = envelope.answer_text
                yield f"event: text_delta\ndata: {json.dumps({'content': envelope.answer_text}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"[mascot] 流式回答失败: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"
            return

        # 2) Engine-driven proactive actions (new event name).
        try:
            for action in (envelope.proactive_actions or []):
                payload = {
                    "type": action.action_type.value,
                    "priority": action.priority.value,
                    "payload": action.action_payload,
                }
                yield f"event: proactive_action\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.debug(f"[mascot] 引擎 proactive_actions emit 失败: {e}")

        # 3) Command extraction (preserve existing UX)
        for cmd_event in _emit_commands(assistant_message):
            yield cmd_event

        # 4) Link extraction (preserve existing UX)
        try:
            links = _extract_links(req.student_id, req.message, assistant_message)
            for link in links:
                yield f"event: link\ndata: {json.dumps(link, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.debug(f"[mascot] 链接提取失败: {e}")

        # 5) Legacy keyword-based proactive actions (preserved for backward compat).
        # Old clients may still be subscribed to "action"; new clients prefer
        # the structured "proactive_action" emitted above.
        try:
            proactive = _get_proactive_actions(req.student_id, assistant_message)
            for action in proactive:
                yield f"event: action\ndata: {json.dumps(action, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.debug(f"[mascot] 主动推送决策失败: {e}")

        # 6) Done event (preserve existing shape)
        yield f"event: done\ndata: {json.dumps({'full_text': assistant_message}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _emit_commands(text: str):
    """从回复文本中提取并 yield 命令事件。此函数在 event_stream 内部调用。"""
    import re
    # [navigate:目标] → 导航命令
    nav_match = re.search(r'\[navigate:([^\]]+)\]', text)
    if nav_match:
        target = nav_match.group(1).strip()
        yield f"event: command\ndata: {json.dumps({'tag': 'navigate', 'content': target}, ensure_ascii=False)}\n\n"
    # [expression:表情] → 表情命令
    expr_match = re.search(r'\[expression:([^\]]+)\]', text)
    if expr_match:
        expr = expr_match.group(1).strip()
        yield f"event: command\ndata: {json.dumps({'tag': 'expression', 'content': expr}, ensure_ascii=False)}\n\n"


def _extract_links(student_id: str, question: str, answer: str) -> list[dict]:
    """从回答中提取学习链接。"""
    links = []
    # 检测是否提到了课程相关的关键词
    keywords = {
        "Python": ("/course-learn.html", "Python 课程", "📚"),
        "算法": ("/assessment.html", "算法练习", "🧮"),
        "数据库": ("/course-learn.html", "数据库课程", "🗄️"),
        "课程": ("/courses.html", "课程中心", "📖"),
        "练习": ("/assessment.html", "去练习", "✏️"),
        "代码": ("/code.html", "代码工坊", "💻"),
        "数据看板": ("/personal.html", "学习数据", "📊"),
        "学习路径": ("/personal.html", "我的学习路径", "🗺️"),
        "苏格拉底": ("/socratic-ai.html", "苏格拉底教学", "🏛️"),
    }
    for keyword, (url, title, icon) in keywords.items():
        if keyword in question or keyword in answer:
            links.append({
                "title": title,
                "url": url,
                "type": "internal",
                "description": f"点击前往「{title}」",
                "icon": icon,
            })
            if len(links) >= 3:
                break
    return links


def _get_proactive_actions(student_id: str, answer: str) -> list[dict]:
    """生成主动推送动作。

    规则覆盖以下场景（与 tutor_engine/proactive_advisor.py 保持概念一致，
    但不依赖其内部数据结构，确保两端决策逻辑独立演进时不互相阻塞）：

      CRITICAL — 连续错误/放弃信号
      HIGH     — 困难求助/负面情绪
      NORMAL   — 学习提醒/练习建议
      LOW      — 鼓励/签到引导

    所有规则统一使用 mascot API 的数据源：
      - 用户画像: _build_user_profile_text() → /api/profile/
      - 学习统计: _build_today_stats() → study_sessions 表
      - 记忆: 通过 /api/memories/ 管理
    """
    actions = []

    # ── CRITICAL: 放弃信号 ──
    if any(w in answer for w in ["放弃", "不想学了", "学不下去了"]):
        actions.append({
            "type": "proactive",
            "action_type": "struggle_intervention",
            "title": "💜 别放弃，一起想办法",
            "content": "学习中遇到挫折是正常的。休息一下，换个思路，或者从简单的内容重新开始。我一直在这里陪着你。",
            "action_label": "获取学习建议",
            "priority": "critical",
        })

    # ── HIGH: 困难/负面情绪 ──
    negative_words = ["不会", "不懂", "太难", "失败", "沮丧", "不行", "好难", "做不出来"]
    if any(w in answer for w in negative_words):
        actions.append({
            "type": "proactive",
            "action_type": "encourage",
            "title": "💪 相信自己",
            "content": "每个人都是从不会到会的！休息一下，换个思路，再试一次。需要我给你一些提示吗？",
            "action_label": "获取提示",
            "priority": "high",
        })

    # ── NORMAL: 代码相关 → 建议去代码工坊 ──
    code_keywords = ["代码", "bug", "报错", "debug", "调试", "编程", "Python", "写代码"]
    if any(w in answer for w in code_keywords):
        actions.append({
            "type": "proactive",
            "action_type": "practice_prompt",
            "title": "💻 去代码工坊练习",
            "content": "动手实践是最好的学习方式。代码工坊有 AI 结对编程和实时诊断，去试试吧！",
            "action_label": "打开代码工坊",
            "priority": "normal",
        })

    # ── LOW: 学习时长 ≥30分钟 → 提醒休息 ──
    try:
        today_stats = _build_today_stats(student_id)
        import re
        minutes_match = re.search(r'(\d+)\s*分钟', today_stats)
        if minutes_match and int(minutes_match.group(1)) >= 30:
            actions.append({
                "type": "proactive",
                "action_type": "health_reminder",
                "title": "🧘 适当休息",
                "content": f"你已经学习了 {minutes_match.group(1)} 分钟，起来活动一下，喝杯水吧！",
                "action_label": "开始番茄钟",
                "priority": "low",
            })
    except Exception:
        pass

    return actions


# =============================================================================
# 快速学习统计
# =============================================================================

@router.get("/stats/{user_id}")
async def get_quick_stats(user_id: str):
    """Quick learning stats via Repository."""
    try:
        from app.core.repository_factory import get_repository_for_user
        repo = get_repository_for_user(user_id, repository_type="learning")
        # Note: LearningRepository.get_overview is a SYNC method despite the
        # Protocol declaring it as async — see app/repositories/legacy/learning.py
        # and app/repositories/orm/learning.py. Pre-existing signature mismatch
        # from M3 learning-read; tracked as a separate follow-up to align the
        # Protocol. Calling without `await` here so the endpoint actually works.
        overview = repo.get_overview(user_id)
        return {
            "success": True,
            "stats": overview,
        }
    except Exception as e:
        logger.error(f"[mascot] get_quick_stats 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 每日签到
# =============================================================================

@router.post("/checkin")
async def daily_checkin(req: MascotCheckinRequest):
    """Daily check-in via Repository (records as a zero-minute study session)."""
    try:
        from app.core.repository_factory import get_repository_for_user
        repo = get_repository_for_user(req.student_id, repository_type="learning")
        # record_session is sync (see comment in get_quick_stats above).
        repo.record_session(req.student_id, {
            "activity_type": "checkin",
            "subject": "daily_checkin",
            "minutes": 0,
            "metadata": {"source": "mascot_daily_checkin"},
        })
        return {"success": True, "streak_days": 1}
    except Exception as e:
        logger.error(f"[mascot] daily_checkin 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 记忆管理 — 统一使用 /api/memories/ (app/api/memory.py)
#
# 小星前端通过 /api/memories/ 读写记忆，与 AI 问答页 (index.js) 共享同一
# 套端点。mascot.py 不再重复暴露 /api/mascot/memories/*。
# =============================================================================


# =============================================================================
# AI 模型配置接口
# =============================================================================

@router.get("/models")
async def list_ai_models():
    """返回小星可用的 AI 大模型列表"""
    from config import settings

    models = [
        {
            "id": "MiniMax-Text-01",
            "name": "MiniMax-Text-01",
            "provider": "MiniMax",
            "description": "通用大语言模型，擅长学习辅导、代码生成、概念讲解",
            "default": True,
            "max_tokens": 8192,
            "available": bool(settings.minimax_api_key),
        },
    ]

    # 如果有讯飞 API Key，也列出
    if settings.xunfei_api_key:
        models.append({
            "id": "astron-code-latest",
            "name": "星火代码大模型",
            "provider": "讯飞",
            "description": "代码专项模型，适合编程与算法学习",
            "default": False,
            "max_tokens": 4096,
            "available": True,
        })

    return {
        "success": True,
        "data": {
            "models": models,
            "default_model": "MiniMax-Text-01",
            "minimax_available": bool(settings.minimax_api_key),
        },
    }


@router.get("/config")
async def get_mascot_config():
    """返回小星面板的运行时配置（模型信息 + 功能开关）"""
    from config import settings

    return {
        "success": True,
        "data": {
            "ai_model": settings.minimax_model_name if settings.minimax_api_key else "unavailable",
            "ai_provider": "MiniMax",
            "ai_available": bool(settings.minimax_api_key),
            "tts_available": bool(settings.minimax_api_key),
            "asr_provider": "baidu-asr" if settings.baidu_asr_api_key else "unavailable",
            "version": "4.0.0",
        },
    }


# =============================================================================
# 用户能力画像 (Slice 12.4)
# =============================================================================

@router.get("/capability/{user_id}")
async def get_capability_profile(user_id: str):
    """Get the 6-dim capability profile for a user.

    Used by the frontend mascot-services.js to:
      - Adjust LLM system prompt based on cognitive_style
      - Show knowledge_base heatmap
      - Highlight weakness in proactive_action toasts
    """
    try:
        from app.services.tutor_engine.capability_aggregator import CapabilityAggregator
        agg = CapabilityAggregator()
        profile = await agg.for_user(user_id)
        return {
            "user_id": user_id,
            "knowledge_base": profile.knowledge_base,
            "code_skill": profile.code_skill,
            "cognitive_style": asdict(profile.cognitive_style),
            "focus_level": asdict(profile.focus_level),
            "learning_goals": [asdict(g) for g in profile.learning_goals],
            "weakness": [asdict(w) for w in profile.weakness],
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"[mascot] get_capability_profile 失败: {e}")
        raise HTTPException(status_code=503, detail=f"Capability aggregation failed: {str(e)[:100]}")
