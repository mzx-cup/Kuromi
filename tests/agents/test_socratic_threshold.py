"""Tests for SocraticEvaluatorAgent forced-questioning threshold (M3.4)."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_socratic_blocks_reveal_below_threshold():
    """turn_count < reveal_threshold 时，禁止揭示答案。"""
    from agents import SocraticEvaluatorAgent

    agent = SocraticEvaluatorAgent(reveal_threshold=3)
    state = {"turn_count": 1, "socratic_pass_rate": 0.5}
    response = await agent.process_answer(
        state=state,
        answer="a² + b² = c²",
        topic="勾股定理",
    )
    assert response["revealed"] is False
    assert response["turn_count"] == 2
    # 提示信息必须包含鼓励继续思考的话术
    msg = response["message"]
    assert "还需" in msg or "继续" in msg or "思考" in msg


@pytest.mark.asyncio
async def test_socratic_allows_reveal_at_or_above_threshold():
    """turn_count >= threshold + pass_rate 高时，揭示答案。"""
    from agents import SocraticEvaluatorAgent

    agent = SocraticEvaluatorAgent(reveal_threshold=3)
    state = {"turn_count": 3, "socratic_pass_rate": 0.8}
    response = await agent.process_answer(
        state=state,
        answer="a² + b² = c²，且仅在直角三角形中成立",
        topic="勾股定理",
    )
    assert response["revealed"] is True
    assert "勾股定理" in response["message"] or "c²" in response["message"]


@pytest.mark.asyncio
async def test_socratic_blocks_reveal_when_pass_rate_low():
    """即使轮数达标，但 pass_rate < 0.6 时仍禁止揭示（防止学生瞎蒙过关）。"""
    from agents import SocraticEvaluatorAgent

    agent = SocraticEvaluatorAgent(reveal_threshold=3)
    state = {"turn_count": 5, "socratic_pass_rate": 0.2}
    response = await agent.process_answer(
        state=state,
        answer="不知道",
        topic="勾股定理",
    )
    assert response["revealed"] is False


@pytest.mark.asyncio
async def test_socratic_default_threshold_is_three():
    """默认 reveal_threshold 应该是 3 轮（计划文档约定）。"""
    from agents import SocraticEvaluatorAgent

    agent = SocraticEvaluatorAgent()
    assert agent.reveal_threshold == 3