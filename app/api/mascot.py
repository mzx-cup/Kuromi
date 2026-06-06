# -*- coding: utf-8 -*-
"""
小星 AI 助手 API — SSE 流式对话 + 学习数据 + 签到

POST /api/mascot/chat/stream  — SSE 流式对话（上下文感知 + 主动推送）
GET  /api/mascot/stats/{user_id} — 快速学习统计
POST /api/mascot/checkin        — 每日签到
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

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
    """构建今日学习统计文本"""
    try:
        sid = _get_student_id_int(student_id)
        from db import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            # 查询今日学习时长
            cursor.execute(
                "SELECT COALESCE(SUM(duration_minutes), 0) FROM study_sessions "
                "WHERE user_id = ? AND session_date = ?",
                (sid, today),
            )
            row = cursor.fetchone()
            today_minutes = row[0] if row else 0

            # 查询连续学习天数
            cursor.execute(
                "SELECT session_date FROM study_sessions "
                "WHERE user_id = ? GROUP BY session_date ORDER BY session_date DESC LIMIT 60",
                (sid,),
            )
            dates = [r[0] for r in cursor.fetchall()]
            streak = 0
            if dates:
                from datetime import timedelta
                check = datetime.now(timezone.utc)
                for date_str in dates:
                    if isinstance(date_str, str):
                        d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
                    else:
                        d = date_str
                    expected = (check - timedelta(days=streak)).date()
                    if d == expected:
                        streak += 1
                    else:
                        break

            cursor.close()
            return f"今日学习 {today_minutes} 分钟, 连续打卡 {streak} 天"
    except Exception as e:
        logger.debug(f"[mascot] 获取今日统计失败: {e}")
        return "暂无统计数据"


def _build_user_profile_text(student_id: str) -> str:
    """构建用户画像文本（精简版）"""
    try:
        from db import get_user_memories
        memories = get_user_memories(student_id, limit=30)
        if not memories:
            return "新用户，还没有学习画像"

        from app.services.profile_aggregator import aggregate_profile
        profile = aggregate_profile(memories)

        parts = []
        # 学习特质
        traits = profile.get("learning_traits", [])
        if traits:
            parts.append("学习特质: " + "、".join(
                t["label"] for t in traits[:3] if t.get("label")
            ))
        # 个性特质
        personality = profile.get("personality_traits", [])
        if personality:
            parts.append("个性: " + "、".join(
                p["label"] for p in personality[:2] if p.get("label")
            ))
        # 目标/兴趣
        goals = profile.get("goals_interests", [])
        if goals:
            parts.append("兴趣/目标: " + "、".join(
                g["label"] for g in goals[:2] if g.get("label")
            ))

        return "; ".join(parts) if parts else "新用户，还没有学习画像"
    except Exception as e:
        logger.debug(f"[mascot] 获取用户画像失败: {e}")
        return "暂无用户画像"


# =============================================================================
# 端点
# =============================================================================

@router.post("/chat/stream")
async def mascot_chat_stream(req: MascotChatRequest):
    """
    小星 SSE 流式对话。

    事件类型:
      event: text_delta   data: {"content": "..."}
      event: command      data: {"tag": "navigate|expression|action", "content": "..."}
      event: action       data: {"type": "proactive", "title": "...", "content": "...", "action_label": "..."}
      event: link         data: {"title": "...", "url": "...", "type": "internal|external", "description": "..."}
      event: done         data: {"full_text": "..."}
      event: error        data: {"message": "..."}
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    # 构建上下文
    page_context = req.page_context or "未知页面"
    user_profile = _build_user_profile_text(req.student_id)
    today_stats = _build_today_stats(req.student_id)

    # 构建系统提示词
    system_prompt = MASCOT_SYSTEM_PROMPT.format(
        page_context=page_context,
        user_profile=user_profile,
        today_stats=today_stats,
    )

    # 构建消息列表
    msg = [{"role": "system", "content": system_prompt}]
    for h in (req.conversation_history or [])[-20:]:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            msg.append({"role": role, "content": content})
    msg.append({"role": "user", "content": req.message})

    async def event_stream():
        from llm_stream import call_llm_stream_with_log_messages

        full_text = ""
        assistant_message = ""

        try:
            # 流式调用 LLM
            stream = await call_llm_stream_with_log_messages(
                system_prompt=system_prompt,
                messages=msg,
                student_id=req.student_id,
                temperature=0.8,
                max_tokens=1024,
                label="mascot_chat",
            )

            async for chunk in stream:
                # chunk 可能是字符串
                content = chunk.get("content", "") if isinstance(chunk, dict) else str(chunk)
                if content:
                    full_text += content
                    assistant_message += content
                    yield f"event: text_delta\ndata: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"[mascot] LLM 流失败: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"
            return

        # 解析命令
        for cmd_event in _emit_commands(assistant_message):
            yield cmd_event

        # 提取并发送链接（如果有）
        links = _extract_links(req.student_id, req.message, assistant_message)
        for link in links:
            yield f"event: link\ndata: {json.dumps(link, ensure_ascii=False)}\n\n"

        # 完成事件
        yield f"event: done\ndata: {json.dumps({'full_text': assistant_message}, ensure_ascii=False)}\n\n"

        # 推送主动动作
        try:
            proactive = _get_proactive_actions(req.student_id, assistant_message)
            for action in proactive:
                yield f"event: action\ndata: {json.dumps(action, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.debug(f"[mascot] 主动推送决策失败: {e}")

    from fastapi.responses import StreamingResponse

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
    """获取快速学习统计（面板顶部数据条）"""
    try:
        sid = _get_student_id_int(user_id)
        from db import get_db
        from datetime import timedelta

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        with get_db() as conn:
            cursor = conn.cursor()

            # 今日学习时长
            cursor.execute(
                "SELECT COALESCE(SUM(duration_minutes), 0) FROM study_sessions "
                "WHERE user_id = ? AND session_date = ?",
                (sid, today),
            )
            today_minutes = (cursor.fetchone() or [0])[0]

            # 本周学习时长
            week_start = (datetime.now(timezone.utc) - timedelta(days=datetime.now(timezone.utc).weekday())).strftime("%Y-%m-%d")
            cursor.execute(
                "SELECT COALESCE(SUM(duration_minutes), 0) FROM study_sessions "
                "WHERE user_id = ? AND session_date >= ?",
                (sid, week_start),
            )
            week_minutes = (cursor.fetchone() or [0])[0]

            # 连续学习天数
            cursor.execute(
                "SELECT session_date FROM study_sessions "
                "WHERE user_id = ? GROUP BY session_date ORDER BY session_date DESC LIMIT 60",
                (sid,),
            )
            dates = [r[0] for r in cursor.fetchall()]
            streak = 0
            if dates:
                check = datetime.now(timezone.utc)
                for date_str in dates:
                    if isinstance(date_str, str):
                        d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
                    else:
                        d = date_str
                    expected = (check - timedelta(days=streak)).date()
                    if d == expected:
                        streak += 1
                    else:
                        break

            # 学习课程数
            cursor.execute(
                "SELECT COUNT(DISTINCT subject) FROM study_sessions WHERE user_id = ?",
                (sid,),
            )
            subject_count = (cursor.fetchone() or [0])[0]

            # 待完成任务数（goals）
            cursor.execute(
                "SELECT COUNT(*) FROM goals WHERE user_id = ? AND current_value < target_value",
                (sid,),
            )
            pending_tasks = (cursor.fetchone() or [0])[0]

            cursor.close()

        return {
            "success": True,
            "data": {
                "today_minutes": today_minutes,
                "today_hours": round(today_minutes / 60, 1),
                "week_minutes": week_minutes,
                "week_hours": round(week_minutes / 60, 1),
                "streak_days": streak,
                "subject_count": subject_count or 0,
                "pending_tasks": pending_tasks or 0,
                "weekly_goal_percent": min(100, round(week_minutes / 420 * 100)) if week_minutes else 0,
            },
        }
    except Exception as e:
        logger.warning(f"[mascot] 获取统计失败: {e}")
        return {
            "success": True,
            "data": {
                "today_minutes": 0,
                "today_hours": 0,
                "week_minutes": 0,
                "week_hours": 0,
                "streak_days": 0,
                "subject_count": 0,
                "pending_tasks": 0,
                "weekly_goal_percent": 0,
            },
        }


# =============================================================================
# 每日签到
# =============================================================================

@router.post("/checkin")
async def daily_checkin(req: MascotCheckinRequest):
    """每日签到 — 记录今日签到并返回连续签到天数"""
    try:
        sid = _get_student_id_int(req.student_id)
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        from db import get_db

        with get_db() as conn:
            cursor = conn.cursor()

            # 检查今天是否已签到
            cursor.execute(
                "SELECT id, streak FROM checkins WHERE user_id = ? AND date = ? LIMIT 1",
                (sid, today_str),
            )
            row = cursor.fetchone()

            if row:
                # 今日已签到
                return {
                    "success": True,
                    "is_first_today": False,
                    "streak": row[1] if row[1] else 0,
                    "message": "今天已经签到过了，继续保持！🌟",
                }

            # 获取上次签到
            cursor.execute(
                "SELECT date, streak FROM checkins WHERE user_id = ? ORDER BY date DESC LIMIT 1",
                (sid,),
            )
            last_row = cursor.fetchone()

            new_streak = 1
            if last_row:
                last_date = last_row[0]
                last_streak = last_row[1] or 0
                from datetime import timedelta
                yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
                if last_date == yesterday or last_date == today_str:
                    new_streak = last_streak + 1

            # 记录签到（尝试创建 checkins 表如果不存在）
            try:
                cursor.execute(
                    "INSERT INTO checkins (user_id, date, streak, timestamp) VALUES (?, ?, ?, ?)",
                    (sid, today_str, new_streak, datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()
            except Exception:
                # checkins 表可能不存在，尝试创建
                try:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS checkins (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            date TEXT NOT NULL,
                            streak INTEGER DEFAULT 1,
                            timestamp TEXT
                        )
                    """)
                    conn.commit()
                    cursor.execute(
                        "INSERT INTO checkins (user_id, date, streak, timestamp) VALUES (?, ?, ?, ?)",
                        (sid, today_str, new_streak, datetime.now(timezone.utc).isoformat()),
                    )
                    conn.commit()
                except Exception as e2:
                    logger.debug(f"[mascot] checkins 表创建失败: {e2}")

            cursor.close()

            # 签到奖励语
            if new_streak >= 30:
                msg = f"🎉 {new_streak}天！你已经坚持了一个月，太厉害了！"
            elif new_streak >= 21:
                msg = f"🌟 {new_streak}天！21天养成一个习惯，你已经做到了！"
            elif new_streak >= 7:
                msg = f"🔥 {new_streak}天！连续一周了，势头正旺！"
            elif new_streak >= 3:
                msg = f"✨ {new_streak}天！好的开始是成功的一半！"
            else:
                msg = f"🌱 Day {new_streak}！千里之行，始于足下！"

            return {
                "success": True,
                "is_first_today": True,
                "streak": new_streak,
                "message": msg,
            }

    except Exception as e:
        logger.warning(f"[mascot] 签到失败: {e}")
        # 降级：基于 localStorage 的方案
        return {
            "success": True,
            "is_first_today": True,
            "streak": 1,
            "message": "🌱 Day 1！千里之行，始于足下！",
        }


# =============================================================================
# 记忆管理 — 统一使用 /api/memories/ (app/api/memory.py)
#
# 小星前端通过 /api/memories/ 读写记忆，与 AI 问答页 (index.js) 共享同一
# 套端点。mascot.py 不再重复暴露 /api/mascot/memories/*。
# =============================================================================
