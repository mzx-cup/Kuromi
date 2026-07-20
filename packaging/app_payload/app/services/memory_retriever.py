# -*- coding: utf-8 -*-
"""
Memory Retriever — 检索与用户当前问题相关的长期记忆

用于在每次聊天前，从用户记忆库中找到最相关的记忆，
注入到 system prompt 中，让 AI 自然地引用过往信息。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("starlearn.memory")


def _retrieve_memories_core(user_id: str, current_input: str, limit: int, min_confidence: float) -> list[dict[str, Any]]:
    """核心检索逻辑（同步）。"""
    from app.repositories.legacy.chat import DbPyChatRepository

    chat_repo = DbPyChatRepository()
    all_memories = chat_repo.get_memories(user_id, limit=200)
    if not all_memories:
        return []

    filtered = [m for m in all_memories if m.get("confidence", 1.0) >= min_confidence]

    current_words = set(_tokenize(current_input))
    scored = []
    for mem in filtered:
        mem_words = set(_tokenize(mem.get("content", "")))
        overlap = len(current_words & mem_words)
        score = overlap
        score += mem.get("confidence", 1.0) * 0.5
        score += min(mem.get("access_count", 1) / 10, 0.3)
        if mem.get("confirmed"):
            score += 0.2
        scored.append((score, mem))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_memories = [m for _, m in scored[:limit]]

    for mem in top_memories:
        try:
            chat_repo.bump_memory_access(int(mem.get("id")))
        except Exception:
            pass

    logger.info(f"[MemoryRetriever] 为用户 {user_id} 检索到 {len(top_memories)} 条相关记忆")
    return top_memories


async def retrieve_relevant_memories(
    user_id: str,
    current_input: str,
    limit: int = 8,
    min_confidence: float = 0.5,
) -> list[dict[str, Any]]:
    """异步包装。"""
    return _retrieve_memories_core(user_id, current_input, limit, min_confidence)


def retrieve_relevant_memories_sync(
    user_id: str,
    current_input: str,
    limit: int = 8,
    min_confidence: float = 0.5,
) -> list[dict[str, Any]]:
    """同步版本（供同步函数调用）。"""
    return _retrieve_memories_core(user_id, current_input, limit, min_confidence)


def retrieve_memories_with_logs(
    user_id: str,
    current_input: str,
    limit: int = 8,
    min_confidence: float = 0.5,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    检索记忆并返回检索日志（用于thinking链路展示）。
    Returns: (memories, retrieval_logs)
    """
    from app.repositories.legacy.chat import DbPyChatRepository

    chat_repo = DbPyChatRepository()
    all_memories = chat_repo.get_memories(user_id, limit=200)
    if not all_memories:
        return [], []

    filtered = [m for m in all_memories if m.get("confidence", 1.0) >= min_confidence]
    current_words = set(_tokenize(current_input))

    scored = []
    for mem in filtered:
        mem_words = set(_tokenize(mem.get("content", "")))
        overlap = len(current_words & mem_words)
        score = overlap
        score += mem.get("confidence", 1.0) * 0.5
        score += min(mem.get("access_count", 1) / 10, 0.3)
        if mem.get("confirmed"):
            score += 0.2
        scored.append((score, mem))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_memories = [m for _, m in scored[:limit]]

    logs = []
    for score, mem in scored[:limit]:
        logs.append({
            "memory_id": mem.get("id"),
            "content": mem.get("content", ""),
            "relevance_score": round(score, 2),
            "memory_type": mem.get("memory_type", "fact"),
        })
        try:
            chat_repo.bump_memory_access(int(mem.get("id")))
        except Exception:
            pass

    logger.info(f"[MemoryRetriever] 为用户 {user_id} 检索到 {len(top_memories)} 条相关记忆")
    return top_memories, logs


def format_memories_for_prompt(memories: list[dict[str, Any]]) -> str:
    """将记忆格式化为可注入 system prompt 的文本，要求 AI 显性引用并添加标记。"""
    if not memories:
        return ""

    type_labels = {
        "background": "📋 个人背景",
        "preference": "⭐ 偏好习惯",
        "knowledge": "📚 已学知识",
        "interest": "💡 兴趣方向",
        "goal": "🎯 学习目标",
        "emotion": "💭 情感记录",
        "learning_trait": "🔍 学习特征",
        "personality": "🧠 性格特点",
        "interaction": "🤝 交互记录",
    }

    lines = ["\n【关于这位学生的已知信息（请在回答中自然地引用）】:"]
    for mem in memories:
        label = type_labels.get(mem.get("memory_type", "fact"), "📝 其他")
        content = mem.get("content", "")
        lines.append(f"  {label}: {content}")

    lines += [
        "",
        "【记忆引用要求】:",
        "1. 当以上信息与当前问题相关时，请使用以下显性句式之一关联：",
        '   - "我记得你之前提到过..."',
        '   - "既然你已经学过..."',
        '   - "考虑到你的背景是..."',
        '   - "结合你之前说的..."',
        '   - "根据你之前分享的信息..."',
        "2. 引用时请在引用内容前后添加标记：[MemRef]引用内容[/MemRef]",
        "3. 引用要自然融入回答，不要生硬罗列，不要每句话都引用",
        "4. 如果没有相关记忆，则正常回答，不要强行引用",
        "",
    ]
    return "\n".join(lines)


def _tokenize(text: str) -> list[str]:
    """简单中文分词（基于字符+短词）。"""
    import re
    # 提取中文字符和英文单词
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    english_words = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    # 中文按字分，英文按词分
    return chinese_chars + english_words
