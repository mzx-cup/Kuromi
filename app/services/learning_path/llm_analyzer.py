# -*- coding: utf-8 -*-
"""
学习路径节点状态 LLM 综合分析器

双轨制中的"软判断"侧：从对话、代码调试等无法被规则量化的行为中，
捕捉学生是否真正理解某知识点。

当 LLM 判断已掌握但规则引擎未达标时，标记为 mastered 并建议验证测验。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import db as database
from app.core.repository_factory import get_repository_for_user
from config import settings


def _course_progress_repo(user_id):
    """CourseProgressRepository instance routed for this user."""
    return get_repository_for_user(str(user_id), repository_type="course_progress")


@dataclass
class LLMNodeAnalysis:
    """LLM 对单个知识点的分析结果"""
    node_id: str
    understood: bool                      # LLM 是否判断学生已理解
    confidence: float                     # LLM 判断置信度 0-1
    reasoning: str                        # 判断理由
    evidence_quotes: list[str]            # 支撑判断的对话原文引用
    suggested_action: str                 # 建议动作
    recommend_quiz: bool                  # 是否建议补充测验验证


SYSTEM_PROMPT = """你是一位资深教育学评估专家，擅长从学生的对话和代码行为中判断其真实理解水平。

## 任务
根据提供的"学生与 AI 的对话记录"和"当前知识点信息"，判断学生是否已经真正理解该知识点。

## 判断标准（满足任意一项即算理解）
1. **概念复述准确**：学生能用自己的话准确复述知识点的核心概念
2. **举一反三**：学生能将知识点应用到新场景或不同语境
3. **深度追问**：学生能提出该知识点的进阶问题（边界情况、优缺点、对比等）
4. **代码实践正确**：学生编写的代码体现了对该知识点的正确运用
5. **错误自纠**：学生能在引导下发现自己的错误并正确修正

## 输出格式（纯 JSON）
```json
{
  "understood": true | false,
  "confidence": 0.0~1.0,
  "reasoning": "判断理由（1-3句话）",
  "evidence_quotes": ["支撑判断的对话原文片段1", "片段2"],
  "suggested_action": "建议下一步动作",
  "recommend_quiz": true | false
}
```

## 重要原则
- 不要只看学生说了"我懂了"，要看实际表达的内容
- 如果学生只是重复 AI 的话而没有内化，不算真正理解
- 如果学生能指出知识点之间的关联和区别，是理解的强信号
- confidence >= 0.8 才算高置信度判断
- 当 understood=true 但缺少客观测验验证时，recommend_quiz=true
"""


def _call_llm_for_analysis(messages: list[dict], node_topic: str) -> dict | None:
    """调用 LLM 进行知识点理解度分析"""
    import requests

    user_prompt = f"""## 评估知识点：{node_topic}

## 学生近期对话记录
{json.dumps(messages, ensure_ascii=False, indent=2)}

请基于以上对话，判断学生是否已经真正理解「{node_topic}」。只输出 JSON，不要其他内容。"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.minimax_api_key}",
    }
    payload = {
        "model": settings.minimax_model_name,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
    }
    try:
        resp = requests.post(
            f"{settings.minimax_api_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        body = resp.json()
        content = body["choices"][0]["message"]["content"]

        # 提取 JSON
        import re
        json_match = re.search(r'\{[\s\S]*?\}', content)
        if json_match:
            return json.loads(json_match.group())
        return None
    except Exception as e:
        print(f"[LLMAnalyzer] LLM 调用失败: {e}")
        return None


def analyze_node_from_conversation(
    user_id: str | int,
    node_id: str,
    recent_messages: list[dict] | None = None,
) -> LLMNodeAnalysis | None:
    """
    基于学生与 AI 的近期对话，分析其是否理解某知识点。

    Args:
        user_id: 学生 ID
        node_id: 知识点节点 ID
        recent_messages: 可选，直接传入对话记录；否则从数据库读取

    Returns:
        LLMNodeAnalysis 或 None（如果无法分析）
    """
    # 获取节点信息
    course_progress_repo = _course_progress_repo(user_id)
    node = course_progress_repo.get_learning_path_node(user_id, node_id)
    if not node:
        return None

    node_topic = node.get('node_topic') or node_id.split(':')[-1].replace('_', '')

    # 获取对话记录
    if recent_messages is None:
        recent_messages = _get_recent_messages_for_node(user_id, node_topic)

    if not recent_messages or len(recent_messages) < 2:
        return None  # 对话太少，无法分析

    # 调用 LLM 分析
    llm_result = _call_llm_for_analysis(recent_messages, node_topic)
    if not llm_result:
        return None

    return LLMNodeAnalysis(
        node_id=node_id,
        understood=llm_result.get('understood', False),
        confidence=llm_result.get('confidence', 0.0),
        reasoning=llm_result.get('reasoning', ''),
        evidence_quotes=llm_result.get('evidence_quotes', []),
        suggested_action=llm_result.get('suggested_action', ''),
        recommend_quiz=llm_result.get('recommend_quiz', False),
    )


def apply_llm_analysis(user_id: str | int, analysis: LLMNodeAnalysis) -> bool:
    """
    将 LLM 分析结果应用到节点状态。

    策略：
    - understood + confidence >= 0.8：标记 llm_verified=1
    - understood + confidence >= 0.8 + recommend_quiz=True：标记 mastered（待验证）
    - understood + confidence < 0.8：不做状态变更，仅记录分析
    """
    course_progress_repo = _course_progress_repo(user_id)
    existing = course_progress_repo.get_learning_path_node(user_id, analysis.node_id)
    if not existing:
        return False

    node_data = {
        'node_id': analysis.node_id,
        'node_topic': existing.get('node_topic'),
        'llm_verified': 1 if analysis.understood and analysis.confidence >= 0.7 else 0,
        'evidence_json': {
            'llm_analysis': {
                'understood': analysis.understood,
                'confidence': analysis.confidence,
                'reasoning': analysis.reasoning,
                'evidence_quotes': analysis.evidence_quotes,
                'suggested_action': analysis.suggested_action,
                'recommend_quiz': analysis.recommend_quiz,
            }
        },
    }

    # 状态判定（双轨制宽松策略）
    current_status = existing.get('status', 'locked')
    rule_verified = existing.get('rule_verified', 0)

    if analysis.understood and analysis.confidence >= 0.8:
        # LLM 高置信度判断已理解
        if rule_verified:
            # 双轨都确认 → completed
            node_data['status'] = 'completed'
            node_data['completion_source'] = 'llm_inferred'
            node_data['mastery_score'] = max(existing.get('mastery_score', 0), 85.0)
        else:
            # LLM 确认但规则未达标 → mastered（待验证）
            node_data['status'] = 'mastered'
            node_data['mastery_score'] = max(existing.get('mastery_score', 0), 75.0)
    elif analysis.understood and analysis.confidence >= 0.6:
        # 中等置信度 → 提升掌握度但不改变状态
        node_data['mastery_score'] = max(existing.get('mastery_score', 0), 60.0)
        if current_status == 'locked':
            node_data['status'] = 'in_progress'

    success = course_progress_repo.save_learning_path_node(user_id, node_data)
    if success:
        print(f"[LLMAnalyzer] 节点 {analysis.node_id} LLM分析完成: "
              f"understood={analysis.understood}, confidence={analysis.confidence}, "
              f"status={node_data.get('status', current_status)}")
    return success


def _get_recent_messages_for_node(user_id, node_topic: str) -> list[dict]:
    """获取与某知识点相关的近期对话记录"""
    # 获取最近 20 条对话消息
    try:
        raw_msgs = database.get_recent_messages_summary(user_id, limit=20)
    except Exception:
        raw_msgs = []

    messages = []
    node_keywords = set(node_topic.lower().replace('_', ''))

    for msg in raw_msgs:
        content = msg.get('content', '')
        if not content:
            continue
        # 简单过滤：消息内容与知识点相关的才保留
        content_lower = content.lower()
        if any(kw in content_lower for kw in node_keywords):
            messages.append({
                'role': msg.get('role', 'user'),
                'content': content[:500],  # 截断避免过长
            })
        else:
            # 也保留一些上下文（前后各保留少量无关消息）
            if len(messages) > 0 and messages[-1].get('role') != msg.get('role'):
                messages.append({
                    'role': msg.get('role', 'user'),
                    'content': content[:200],
                })

    return messages[-15:]  # 最多保留 15 条


# ── TutorDecisionEngine 集成入口 ──

def analyze_after_chat(
    user_id: str | int,
    node_id: str | None,
    conversation_messages: list[dict],
) -> LLMNodeAnalysis | None:
    """
    聊天对话后调用，分析学生是否理解了当前讨论的知识点。

    这是 TutorDecisionEngine 的集成入口。
    """
    if not node_id:
        # 尝试从对话内容推断知识点
        node_id = _infer_node_from_messages(conversation_messages)
        if not node_id:
            return None

    analysis = analyze_node_from_conversation(
        user_id=user_id,
        node_id=node_id,
        recent_messages=conversation_messages,
    )
    if analysis:
        apply_llm_analysis(user_id, analysis)
    return analysis


def _infer_node_from_messages(messages: list[dict]) -> str | None:
    """从对话内容推断当前讨论的知识点"""
    # 简单实现：取最近 AI 回复中提到的第一个知识点
    # TODO: 更智能的实现可以使用关键词匹配或 LLM 提取
    for msg in reversed(messages):
        if msg.get('role') == 'assistant':
            content = msg.get('content', '')
            # 简单匹配：查找「关于...」或「...知识点」
            import re
            matches = re.findall(r'[「【](.+?)[」】]|(?:关于|讲解|学习)([^，。,\s]{2,20})', content)
            if matches:
                topic = matches[0][0] or matches[0][1]
                topic_clean = re.sub(r'[^\w一-鿿]+', '_', topic).strip('_').lower()
                return f"topic:{topic_clean}"
    return None
