"""Tests for ReflectionLogAgent (M5.4)."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_agent_returns_three_metacognitive_questions():
    """generate_questions(topic) 必须返回 3 个元认知问题。"""
    from app.services.reflection.log_agent import ReflectionLogAgent

    agent = ReflectionLogAgent()
    questions = await agent.generate_questions(topic="勾股定理")
    assert len(questions) == 3
    # 必须包含三个元认知维度
    assert any("卡在哪" in q for q in questions)
    assert any("换条件" in q or "换一种" in q for q in questions)
    assert any("复述" in q or "讲给" in q or "讲一遍" in q for q in questions)


@pytest.mark.asyncio
async def test_agent_aggregates_weekly_reflections():
    """aggregate_weekly 必须按 topic 分组 + 计数。"""
    from app.services.reflection.log_agent import ReflectionLogAgent

    agent = ReflectionLogAgent()
    reflections = [
        {"user_id": "u1", "topic": "勾股定理", "answer": "卡在 a²+b²=c² 的推导"},
        {"user_id": "u1", "topic": "勾股定理", "answer": "原来要画辅助线"},
        {"user_id": "u2", "topic": "三角函数", "answer": "完全不懂"},
    ]
    aggregated = await agent.aggregate_weekly(reflections)
    assert "勾股定理" in aggregated
    assert aggregated["勾股定理"]["count"] == 2
    assert "三角函数" in aggregated
    assert aggregated["三角函数"]["count"] == 1


@pytest.mark.asyncio
async def test_agent_aggregate_empty_list():
    """空列表聚合必须返回空 dict（不崩）。"""
    from app.services.reflection.log_agent import ReflectionLogAgent

    agent = ReflectionLogAgent()
    aggregated = await agent.aggregate_weekly([])
    assert aggregated == {}


@pytest.mark.asyncio
async def test_agent_questions_have_topic_suffix():
    """每个问题末尾必须带上 topic，便于学生关联上下文。"""
    from app.services.reflection.log_agent import ReflectionLogAgent

    agent = ReflectionLogAgent()
    questions = await agent.generate_questions(topic="一元二次方程")
    for q in questions:
        assert "一元二次方程" in q