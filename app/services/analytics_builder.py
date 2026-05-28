"""
学情数据聚合服务 (Student Analytics Builder)

聚合分散在各处的学生数据，构建统一的学情报告，供学习路径生成使用。
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import db as database


def _safe_json(val):
    """安全解析可能是 JSON 字符串的值。"""
    if isinstance(val, str) and val:
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            pass
    return val


def build_student_analytics(user_id: str | int) -> dict[str, Any]:
    """
    聚合学生全量学情数据，返回结构化报告。

    数据源：
      - user_profile（画像）
      - cockpit_analysis（驾驶舱指标）
      - quiz_records（测验记录）
      - classroom_sessions（课堂进度）
      - user_stats（学习时长/统计）
      - daily_route（今日航线）
      - learning_path（当前路径）
      - messages / conversation_summaries（近期对话）
    """
    user_id = str(user_id)

    # 1. 用户画像
    profile_raw = database.get_user_profile(user_id)
    profile_json = _safe_json(profile_raw.get("profile_json")) if profile_raw else {}
    evaluation_json = _safe_json(profile_raw.get("evaluation_json")) if profile_raw else {}

    # 2. 驾驶舱指标（复用计算逻辑）
    cockpit = _build_cockpit_metrics(user_id, evaluation_json)

    # 3. 测验记录
    quizzes = database.get_recent_quizzes(user_id, limit=20)
    quiz_summary = _summarize_quizzes(quizzes)

    # 4. 课堂记录
    classrooms = database.get_recent_classrooms(user_id, limit=10)
    classroom_summary = _summarize_classrooms(classrooms)

    # 5. 学习统计
    stats = database.get_user_stats(user_id) or {}

    # 6. 今日航线
    today = date.today().isoformat()
    daily_route = database.get_daily_route(user_id, today)

    # 7. 当前路径
    path_raw = database.get_learning_path(user_id)
    current_path = _safe_json(path_raw.get("path_json")) if path_raw else []
    path_meta = {
        "generated_at": path_raw.get("generated_at") if path_raw else None,
        "reasoning": path_raw.get("reasoning") if path_raw else None,
        "confidence": path_raw.get("confidence", 0.0) if path_raw else 0.0,
    }

    # 8. 对话摘要
    conv_summaries = database.get_conversation_summary(user_id)
    recent_messages = database.get_recent_messages_summary(user_id, limit=30)

    # 组装报告
    report = {
        "student_id": user_id,
        "generated_at": datetime.now().isoformat(),
        "profile": {
            "learning_style": profile_json.get("learningStyle", "pragmatic"),
            "cognitive_level": profile_json.get("cognitiveLevel", "basic"),
            "learning_goals": profile_json.get("learningGoals", []),
            "knowledge_base": profile_json.get("knowledgeBase", ""),
            "code_skill": profile_json.get("codeSkill", ""),
            "weakness": profile_json.get("weakness", ""),
            "cognitive_style": profile_json.get("cognitiveStyle", "文字型"),
            "focus_level": profile_json.get("focusLevel", "中等专注"),
        },
        "cockpit": cockpit,
        "quizzes": {
            "recent_count": len(quizzes),
            "summary": quiz_summary,
            "records": quizzes[:5],  # 只保留最近5条详情
        },
        "classrooms": {
            "recent_count": len(classrooms),
            "summary": classroom_summary,
        },
        "study_stats": {
            "interaction_count": stats.get("interactionCount", 0),
            "learning_minutes": stats.get("codePracticeTime", 0),
            "completed_tasks": stats.get("completedTasks", 0),
            "focus_sessions": stats.get("focusSessions", 0),
            "flashcards_studied": stats.get("flashcardsStudied", 0),
            "streak_days": stats.get("streakDays", 0),
            "recent_topics": stats.get("recentTopics", []),
        },
        "daily_route": {
            "has_route": daily_route is not None,
            "tasks_count": len(daily_route.get("tasks_json", [])) if daily_route else 0,
            "completed_count": len(daily_route.get("completed_json", [])) if daily_route else 0,
        },
        "current_path": {
            "nodes_count": len(current_path) if isinstance(current_path, list) else 0,
            "meta": path_meta,
            "preview": _preview_path(current_path),
        },
        "conversations": {
            "summaries": conv_summaries,
            "recent_message_count": len(recent_messages),
            "recent_topics": _extract_topics_from_messages(recent_messages),
        },
    }

    return report


def _build_cockpit_metrics(user_id: str | int, evaluation_json: dict) -> dict:
    """复用驾驶舱分析的计算逻辑，构建核心指标。"""
    stats = database.get_user_stats(user_id) or {}
    interaction_count = stats.get("interactionCount", 0)
    learning_minutes = stats.get("codePracticeTime", 0)
    completed_tasks = stats.get("completedTasks", 0)
    focus_sessions = stats.get("focusSessions", 0)

    # 思维深度
    thinking_depth = min(95, 45 + (interaction_count % 50))
    if learning_minutes > 300:
        thinking_depth = min(95, thinking_depth + 15)
    elif learning_minutes > 100:
        thinking_depth = min(95, thinking_depth + 8)

    # 概念掌握率
    concept_mastery = min(95, 50 + (completed_tasks % 40))
    if interaction_count > 50:
        concept_mastery = min(95, concept_mastery + 10)

    # 专注休息比
    focus_ratio = min(95, 60 + (focus_sessions * 5))
    rest_ratio = 100 - focus_ratio if focus_ratio < 95 else 5

    # 学习动能
    momentum = min(98, 40 + (interaction_count % 50) + (completed_tasks % 20))
    if learning_minutes > 200:
        momentum = min(98, momentum + 10)

    # 认知等级
    if thinking_depth >= 85:
        cognitive_level = "L4·专家级"
    elif thinking_depth >= 70:
        cognitive_level = "L3·进阶级"
    elif thinking_depth >= 55:
        cognitive_level = "L2·基础级"
    else:
        cognitive_level = "L1·入门级"

    return {
        "thinking_depth": thinking_depth,
        "concept_mastery": concept_mastery,
        "focus_ratio": focus_ratio,
        "rest_ratio": rest_ratio,
        "learning_momentum": momentum,
        "cognitive_level": cognitive_level,
        "interaction_count": interaction_count,
        "learning_minutes": learning_minutes,
        "completed_tasks": completed_tasks,
        "focus_sessions": focus_sessions,
    }


def _summarize_quizzes(quizzes: list[dict]) -> dict:
    """汇总测验记录，提取薄弱知识点。"""
    if not quizzes:
        return {"avg_score": 0, "pass_rate": 0, "weak_areas": [], "strong_areas": []}

    total_score = 0
    total_full = 0
    passed_count = 0
    weak_areas = []
    strong_areas = []

    for q in quizzes:
        score = float(q.get("score", 0))
        full = int(q.get("total", 1))
        total_score += score
        total_full += full
        if q.get("passed"):
            passed_count += 1
            if score / full >= 0.85:
                strong_areas.append(q.get("quiz_id", ""))
        else:
            weak_areas.append(q.get("quiz_id", ""))

    avg = round((total_score / total_full) * 100, 1) if total_full else 0
    pass_rate = round(passed_count / len(quizzes) * 100, 1) if quizzes else 0

    return {
        "avg_score": avg,
        "pass_rate": pass_rate,
        "weak_areas": list(set(weak_areas))[:5],
        "strong_areas": list(set(strong_areas))[:5],
    }


def _summarize_classrooms(classrooms: list[dict]) -> dict:
    """汇总课堂记录。"""
    if not classrooms:
        return {"total_time_spent": 0, "completed_count": 0, "active_count": 0, "recent_courses": []}

    total_time = sum(int(c.get("time_spent", 0)) for c in classrooms)
    completed = sum(1 for c in classrooms if c.get("status") == "completed")
    active = sum(1 for c in classrooms if c.get("status") == "active")
    courses = list({c.get("course_id", "") for c in classrooms if c.get("course_id")})[:5]

    return {
        "total_time_spent": total_time,
        "completed_count": completed,
        "active_count": active,
        "recent_courses": courses,
    }


def _preview_path(current_path) -> list[dict]:
    """提取路径预览（前10个节点）。"""
    if not isinstance(current_path, list):
        return []
    preview = []
    for node in current_path[:10]:
        if isinstance(node, dict):
            preview.append({
                "topic": node.get("topic", node.get("name", node.get("title", ""))),
                "status": node.get("status", "locked"),
            })
    return preview


def _extract_topics_from_messages(messages: list[dict]) -> list[str]:
    """从近期消息中简单提取可能的学习主题（取用户消息内容的前20字）。"""
    topics = []
    for msg in messages:
        if msg.get("role") == "user" and msg.get("content"):
            text = msg["content"].strip()
            if len(text) > 3:
                topics.append(text[:30])
    return topics[:5]
