"""Tests for OrchestratorChain (M2.4)."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_chain_executes_links_in_order():
    """链路必须按声明顺序执行 link，每个 link 修改 state。"""
    from app.services.orchestrator.chain import ChainLink, OrchestratorChain

    calls: list[str] = []

    async def step_a(state):
        calls.append("a")
        return {"from": "a"}

    async def step_b(state):
        calls.append("b")
        state["from"] = "b"
        return state

    chain = OrchestratorChain([ChainLink(name="a", fn=step_a), ChainLink(name="b", fn=step_b)])
    result = await chain.run(initial_state={})

    assert calls == ["a", "b"]
    assert result.state["from"] == "b"
    assert result.success is True
    assert result.links_executed == ["a", "b"]


@pytest.mark.asyncio
async def test_chain_retries_on_failure_then_succeeds():
    """某个 link 失败必须自动重试，达到 max_retries 才放弃。"""
    from app.services.orchestrator.chain import ChainLink, OrchestratorChain

    attempts = {"b": 0}

    async def step_a(state):
        return {"x": 1}

    async def step_b(state):
        attempts["b"] += 1
        if attempts["b"] < 2:
            raise ValueError("transient error")
        state["x"] = 2
        return state

    chain = OrchestratorChain(
        [ChainLink(name="a", fn=step_a), ChainLink(name="b", fn=step_b, max_retries=3)],
    )
    result = await chain.run({})
    assert result.success is True
    assert attempts["b"] == 2
    assert result.state["x"] == 2


@pytest.mark.asyncio
async def test_chain_fails_after_max_retries_exhausted():
    """超过 max_retries 后必须以 success=False 终止，记录错误。"""
    from app.services.orchestrator.chain import ChainLink, OrchestratorChain

    async def step_a(state):
        return {"x": 1}

    async def step_b(state):
        raise RuntimeError("permanent failure")

    chain = OrchestratorChain(
        [ChainLink(name="a", fn=step_a), ChainLink(name="b", fn=step_b, max_retries=2)],
    )
    result = await chain.run({})
    assert result.success is False
    assert len(result.errors) >= 1
    assert "permanent failure" in result.errors[0]


def test_chain_requires_at_least_one_link():
    """构造空链必须报错。"""
    from app.services.orchestrator.chain import OrchestratorChain

    with pytest.raises(ValueError):
        OrchestratorChain([])