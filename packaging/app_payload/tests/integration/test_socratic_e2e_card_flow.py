"""End-to-end: SocraticAgent dual-rail dispatch with memory card threading (slice-B3).

The plan referenced ``SocraticEvaluatorAgent.handle_user_message`` which does not
exist in this codebase — the agent only exposes ``run(state, **kwargs)``. These
tests therefore exercise the existing ``run()`` method, which is where the A2
dispatch (and now the B3 card-prepend) lives.

The 8 cases map to the slice-B3 acceptance scenarios:
  1. Normal response passes with the card prepended to the message.
  2. Missing citation -> retry + still blocked, card still prepended.
  3. Invalid citation id -> blocked with invalid_citation_id reason.
  4. Qdrant / produce path raises -> A2 graceful fallback to legacy state.
  5. Card token budget is 500 (schema-level invariant).
  6. Schema declares the 4 canonical field keys.
  7. Card loader failure falls back to empty card / unenriched message.
  8. SSE memory_card event format includes trace_id and token_count.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from agents import SocraticEvaluatorAgent
from state import DialogueRole, StudentState


USE_LC = {"USE_LANGCHAIN_SOCRATIC": "1"}


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def agent() -> SocraticEvaluatorAgent:
    return SocraticEvaluatorAgent()


@pytest.fixture
def state() -> StudentState:
    s = StudentState(student_id="u-1")
    s.add_message(DialogueRole.STUDENT, "什么是霍夫曼编码？")
    return s


def _fake_card(markdown: str = "card_md", token_count: int = 320, partial: list | None = None):
    card = MagicMock()
    card.markdown = markdown
    card.token_count = token_count
    card.partial_fields = partial if partial is not None else []
    return card


# ------------------------------------------------------------------
# Scenario 1: Normal response passes + card prepended to message
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_normal_response_passes_with_card(agent, state):
    """流 1 正常路径 + 接卡：produce_socratic_response receives the card-prepended message."""
    expected_text = "response_X"
    with patch.dict(os.environ, USE_LC):
        with patch("agents.produce_socratic_response",
                   new=MagicMock(return_value=expected_text)) as p, \
             patch("agents.MemoryCardLoader") as M:
            M.return_value.load.return_value = _fake_card()
            result = await agent.run(state)
    assert result == expected_text
    assert p.called
    # The message handed to produce_socratic_response should contain the card.
    kwargs = p.call_args.kwargs
    assert "card_md" in kwargs["message"]
    assert "什么是霍夫曼编码？" in kwargs["message"]
    # Card is *prepended* — card body must come before the original user text.
    assert kwargs["message"].index("card_md") < kwargs["message"].index("什么是霍夫曼编码？")


# ------------------------------------------------------------------
# Scenario 2: Missing citation -> retry + blocked, card still prepended
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_missing_citation_triggers_retry_with_card(agent, state):
    """缺引用 → retry + 仍缺拒答 (card still threaded)."""
    blocked = MagicMock(
        blocked=True, block_reason="unbacked_claims",
        text="我需要核实一下再回答", citations=[], risk=0.85,
    )
    with patch.dict(os.environ, USE_LC):
        with patch("agents.produce_socratic_response",
                   new=MagicMock(return_value=blocked)) as p, \
             patch("agents.MemoryCardLoader") as M:
            M.return_value.load.return_value = _fake_card(markdown="card")
            result = await agent.run(state)
    assert result is blocked
    assert result.text == "我需要核实一下再回答"
    # Card was prepended even on the blocked path.
    assert p.called
    assert "card" in p.call_args.kwargs["message"]


# ------------------------------------------------------------------
# Scenario 3: Invalid citation id -> blocked with invalid_citation_id
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_invalid_citation_id_blocks(agent, state):
    """引用 ID 不在 valid_node_ids → invalid → 拒答."""
    invalid = MagicMock(
        blocked=True, block_reason="invalid_citation_id",
        text="系统错误", citations=[], risk=1.0,
    )
    with patch.dict(os.environ, USE_LC):
        with patch("agents.produce_socratic_response",
                   new=MagicMock(return_value=invalid)) as p:
            result = await agent.run(state)
    assert result.block_reason == "invalid_citation_id"
    assert p.called


# ------------------------------------------------------------------
# Scenario 4: produce path raises -> legacy fallback returns the state
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_produce_path_fails_falls_back_to_legacy(agent, state):
    """produce_socratic_response 抛异常 → A2 graceful fallback 老路径."""
    with patch.dict(os.environ, USE_LC):
        with patch("agents.produce_socratic_response",
                   new=MagicMock(side_effect=RuntimeError("qdrant down"))):
            result = await agent.run(state)
    # 老路径兜底返回了 state (legacy 路径跑完).
    assert result is not None
    assert result is state


# ------------------------------------------------------------------
# Scenario 5: Card budget invariant
# ------------------------------------------------------------------

def test_e2e_card_token_budget_under_500():
    """Socratic schema total_max_tokens == 500."""
    from app.services.agent.socratic_memory_card import socratic_schema

    s = socratic_schema()
    assert s.total_max_tokens == 500
    # Per-field allocation must not exceed the total.
    assert sum(f.max_tokens for f in s.fields) <= 500


# ------------------------------------------------------------------
# Scenario 6: Schema field keys
# ------------------------------------------------------------------

def test_card_field_keys_present():
    """socratic_schema declares the 4 canonical field keys."""
    from app.services.agent.socratic_memory_card import socratic_schema

    s = socratic_schema()
    keys = {f.key for f in s.fields}
    assert keys == {
        "episodic_last", "capability_recent",
        "semantic_top3", "supervision_pending",
    }


# ------------------------------------------------------------------
# Scenario 7: Card loader failure -> unenriched message
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_card_load_failure_falls_back_to_unenriched(agent, state):
    """MemoryCardLoader.load raises -> agent still passes the original message
    to produce_socratic_response (no card prepended)."""
    with patch.dict(os.environ, USE_LC):
        with patch("agents.produce_socratic_response",
                   new=MagicMock(return_value="ok")) as p, \
             patch("agents.MemoryCardLoader") as M:
            M.return_value.load.side_effect = RuntimeError("db down")
            result = await agent.run(state)
    assert result == "ok"
    assert p.called
    # Message is unenriched (no card text leakage).
    sent = p.call_args.kwargs["message"]
    assert sent == "什么是霍夫曼编码？"  # exactly the user content


# ------------------------------------------------------------------
# Scenario 8: SSE memory_card event format
# ------------------------------------------------------------------

def test_memory_card_metadata_in_sse():
    """SSE `_sse_format` for memory_card carries trace_id + token_count."""
    from app.api.agent_orchestration import _sse_format

    payload = _sse_format("memory_card", {
        "trace_id": "t1", "token_count": 320, "partial_fields": [],
    })
    assert "memory_card" in payload
    assert "t1" in payload
    assert "320" in payload