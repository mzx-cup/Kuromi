"""Tests for CriticAgent (M4.4)."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_critic_rejects_vague_answer():
    """模糊答案（缺乏关键术语）必须判为低质量。"""
    from app.agents.critic import CriticAgent, CritiqueResult

    agent = CriticAgent()
    result = await agent.review(
        answer="勾股定理是一个数学概念",
        reference="a² + b² = c²（直角三角形）",
    )
    assert isinstance(result, CritiqueResult)
    assert result.quality in ("low", "medium", "high")
    assert result.score < 0.5


@pytest.mark.asyncio
async def test_critic_accepts_precise_answer():
    """精确答案（包含关键术语）必须判为高质量。"""
    from app.agents.critic import CriticAgent

    agent = CriticAgent()
    result = await agent.review(
        answer="a² + b² = c²，仅在直角三角形中成立",
        reference="a² + b² = c²（直角三角形）",
    )
    assert result.quality == "high"
    assert result.score > 0.85


@pytest.mark.asyncio
async def test_critic_flags_short_answer():
    """过短答案（<10 字符）必须标记 answer_too_short。"""
    from app.agents.critic import CriticAgent

    agent = CriticAgent()
    result = await agent.review(answer="对", reference="勾股定理 a² + b² = c²")
    assert "answer_too_short" in result.issues


@pytest.mark.asyncio
async def test_critic_empty_reference_returns_neutral():
    """reference 为空时必须返回中等分（不崩）。"""
    from app.agents.critic import CriticAgent

    agent = CriticAgent()
    result = await agent.review(answer="勾股定理是数学公式", reference="")
    assert result.score == 0.5
    assert result.quality == "medium"