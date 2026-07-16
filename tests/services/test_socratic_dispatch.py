"""SocraticAgent dual-rail dispatch (slice-A2).

Verifies that ``SocraticEvaluatorAgent.run`` routes through
``produce_socratic_response`` when ``USE_LANGCHAIN_SOCRATIC=1`` and
falls back to the legacy path otherwise (including on exceptions).

NOTE: The plan refers to a ``handle_user_message`` method that does
not exist in this codebase — ``SocraticEvaluatorAgent`` only exposes
``run()`` (per the ``do NOT create a new method`` invariant). These
tests therefore exercise the existing ``run()`` method, which is where
the dispatch is installed.
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from agents import SocraticEvaluatorAgent
from state import DialogueRole, StudentState


@pytest.fixture
def agent():
    return SocraticEvaluatorAgent()


@pytest.fixture
def state():
    s = StudentState(student_id="u-test")
    s.add_message(DialogueRole.STUDENT, "测试")
    return s


@pytest.mark.asyncio
async def test_default_routes_to_legacy_path(agent, state, monkeypatch):
    """USE_LANGCHAIN_SOCRATIC unset / not "1" → legacy run() path."""
    monkeypatch.delenv("USE_LANGCHAIN_SOCRATIC", raising=False)
    with patch("agents.produce_socratic_response", new=MagicMock()) as mock_p:
        result = await agent.run(state)
    assert result is state
    assert not mock_p.called


@pytest.mark.asyncio
async def test_flag_one_routes_to_produce(agent, state, monkeypatch):
    """USE_LANGCHAIN_SOCRATIC=1 → dispatch through produce_socratic_response."""
    monkeypatch.setenv("USE_LANGCHAIN_SOCRATIC", "1")
    with patch(
        "agents.produce_socratic_response",
        new=MagicMock(return_value="new_response"),
    ) as mock_p:
        result = await agent.run(state)
    assert mock_p.called
    assert result == "new_response"


@pytest.mark.asyncio
async def test_flag_one_llm_failure_falls_back_to_legacy(agent, state, monkeypatch):
    """produce_socratic_response raises → silent fallback to legacy."""
    monkeypatch.setenv("USE_LANGCHAIN_SOCRATIC", "1")
    with patch(
        "agents.produce_socratic_response",
        new=MagicMock(side_effect=RuntimeError("qdrant down")),
    ):
        # Must NOT propagate the exception.
        result = await agent.run(state)
    assert result is not None
    # Legacy path returned the original state (post _run_evaluation_only).
    assert result is state


@pytest.mark.asyncio
async def test_empty_env_string_treated_as_zero(agent, state, monkeypatch):
    """USE_LANGCHAIN_SOCRATIC='' → treat as 0 (no new-path dispatch)."""
    monkeypatch.setenv("USE_LANGCHAIN_SOCRATIC", "")
    with patch("agents.produce_socratic_response", new=MagicMock()) as mock_p:
        result = await agent.run(state)
    assert not mock_p.called
    assert result is state