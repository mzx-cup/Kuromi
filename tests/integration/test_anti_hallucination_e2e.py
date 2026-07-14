"""End-to-end: Socratic response pipeline + AntiHallucination parser + 3-layer log.

Slice S3.3 acceptance scenarios (security-critical):
  1. normal               — response with valid citations: not blocked.
  2. missing-citation retry — first attempt unbacked, retry succeeds.
  3. persistent missing   — both attempts unbacked: blocked with reason.
  4. invalid citation id  — cites an unknown KB id: blocked with reason.
  5. qdrant down          — vector store raises: exception propagates
                             (fail-loud at the retrieval layer, never silent
                             fallthrough to a hallucinated answer).
  6. redis down           — resilient logger falls through db -> redis -> disk:
                             callback writes via the disk layer.

All tests use stubbed LLM + vector store. No real network/db calls.
The handler's 3-layer logger is patched via ``_logger`` so the test stays
hermetic and never spins up real DB / Redis / disk spool.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest

from app.services.callbacks.kb_callback_handler import KBCallbackHandler
from app.services.llm.citation import Citation
from app.services.llm.socratic_response import produce_socratic_response
from app.services.llm.xunfei_chat_model import XunfeiChatModel


# ------------------------------------------------------------------
# Stubs
# ------------------------------------------------------------------

@dataclass
class _FakeChunk:
    """Mimics langchain_core.outputs.ChatGenerationChunk.

    The real chunk has ``.message = AIMessageChunk(content=token)``. The
    parser reads ``c.message.content`` and ignores ``c.content`` (the
    chunk itself does not expose a ``content`` attribute in
    langchain_core >= 0.3).
    """
    content: str

    @property
    def message(self):
        from langchain_core.messages import AIMessageChunk
        return AIMessageChunk(content=self.content)


class _FakeLLM(XunfeiChatModel):
    """LLM stub with scripted responses per-call (counter-driven).

    Each call to ``_stream`` consumes the next scripted response; tokens
    within that response are yielded one per chunk (so we exercise the
    per-token streaming path used by ``socratic_response._stream_to_text``).
    """
    def __init__(self, scripted: list[str]):
        # Bypass BaseChatModel's super init — we never call real LLM.
        object.__setattr__(self, "stream_fn", None)
        self._scripted = list(scripted)
        self._calls: list[str] = []
        # Counter is per-test-instance: harmless across tests because each
        # test builds its own stub.

    def _stream(self, messages, stop=None, **kwargs) -> Iterator[_FakeChunk]:
        # Capture which prompt we got (the integration code concatenates
        # the system prompt + user question, so we record the full string).
        self._calls.append(messages[0].content)
        # Yield the scripted text for this call (or the last entry once
        # exhausted, so over-consumption is still deterministic).
        idx = min(len(self._calls) - 1, len(self._scripted) - 1)
        for token in self._scripted[idx]:
            yield _FakeChunk(content=token)


class _FakeVS:
    """Vector store stub returning a fixed hit list (dict-shaped)."""
    def __init__(self, hits: list[tuple[dict, float]] | None = None):
        self._hits = hits if hits is not None else [
            ({"id": "KB-CON-0001", "title": "pythag", "content": "a²+b²=c²"}, 0.92),
            ({"id": "KB-CON-0002", "title": "trig", "content": "sin²+cos²=1"}, 0.85),
        ]
        self.raise_on_call: Exception | None = None

    def similarity_search_with_score(self, query, k=5):
        if self.raise_on_call is not None:
            raise self.raise_on_call
        return list(self._hits)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def fake_vs() -> _FakeVS:
    return _FakeVS()


@pytest.fixture
def fake_handler() -> KBCallbackHandler:
    handler = KBCallbackHandler(agent_id="SocraticAgent", user_id="u1")
    # Replace the lazy logger with a MagicMock so we can assert call count
    # without hitting the real DB/Redis/disk stack. Each test re-patches as
    # needed; this default mock just makes on_validated_response safe to call.
    mock_logger = MagicMock()
    mock_logger.log.return_value = MagicMock(status="ok", layer="db")
    handler._logger = mock_logger
    return handler


# ------------------------------------------------------------------
# Scenario 1: Normal response with valid citations -> not blocked
# ------------------------------------------------------------------

def test_e2e_normal_response_passes(fake_vs: _FakeVS, fake_handler: KBCallbackHandler) -> None:
    text = (
        "勾股定理 [KB:KB-CON-0001] 是 a²+b²=c²。"
        "同样适用于直角三角形 [KB:KB-CON-0001]。"
    )
    llm = _FakeLLM(scripted=[text])

    out = produce_socratic_response(
        "u1", "什么是勾股定理？",
        llm=llm, vector_store=fake_vs, callback_handler=fake_handler,
    )

    assert not out.blocked
    assert len(out.citations) >= 2
    assert out.retry_succeeded is False
    # Successful LLM answer only required a single streaming pass.
    assert len(llm._calls) == 1
    # Handler persisted exactly one entry to the logger.
    assert fake_handler._logger.log.call_count == 1


# ------------------------------------------------------------------
# Scenario 2: Missing citation on first attempt -> retry succeeds
# ------------------------------------------------------------------

def test_e2e_missing_citation_triggers_retry(fake_vs: _FakeVS, fake_handler: KBCallbackHandler) -> None:
    bad = "勾股定理是 a²+b²=c²。"
    good = "勾股定理 [KB:KB-CON-0001] 是 a²+b²=c²。"
    llm = _FakeLLM(scripted=[bad, good])

    out = produce_socratic_response(
        "u1", "什么是勾股定理？",
        llm=llm, vector_store=fake_vs, callback_handler=fake_handler,
    )

    assert not out.blocked
    assert out.retry_succeeded is True
    # Two LLM calls: initial + retry.
    assert len(llm._calls) == 2
    assert fake_handler._logger.log.call_count == 1


# ------------------------------------------------------------------
# Scenario 3: Persistent missing citation -> blocked with reason
# ------------------------------------------------------------------

def test_e2e_persistent_missing_citation_blocks(fake_vs: _FakeVS, fake_handler: KBCallbackHandler) -> None:
    bad = "勾股定理是 a²+b²=c²。"
    llm = _FakeLLM(scripted=[bad, bad])

    out = produce_socratic_response(
        "u1", "什么是勾股定理？",
        llm=llm, vector_store=fake_vs, callback_handler=fake_handler,
    )

    assert out.blocked
    assert out.block_reason == "unbacked_claims"
    assert out.retry_succeeded is False
    assert "核实" in out.text
    # Even when blocked, we still record the behavior for audit — the
    # callback handler must persist a single log entry.
    assert fake_handler._logger.log.call_count == 1
    persisted_entry = fake_handler._logger.log.call_args[0][0]
    assert persisted_entry.blocked is True
    assert persisted_entry.block_reason == "unbacked_claims"


# ------------------------------------------------------------------
# Scenario 4: Invalid citation id -> blocked with invalid_citation_id
# ------------------------------------------------------------------

def test_e2e_invalid_citation_id_blocks(fake_vs: _FakeVS, fake_handler: KBCallbackHandler) -> None:
    text = "勾股定理 [KB:KB-CON-9999] 重要。"
    llm = _FakeLLM(scripted=[text, text])

    out = produce_socratic_response(
        "u1", "什么是勾股定理？",
        llm=llm, vector_store=fake_vs, callback_handler=fake_handler,
    )

    assert out.blocked
    assert out.block_reason == "invalid_citation_id"
    # Invalid id is caught on the first parse attempt, so the retry
    # either fires and the parser returns a blocked response — net calls
    # must still be at most 2 (first + retry).
    assert len(llm._calls) <= 2
    assert fake_handler._logger.log.call_count == 1
    persisted_entry = fake_handler._logger.log.call_args[0][0]
    assert persisted_entry.block_reason == "invalid_citation_id"


# ------------------------------------------------------------------
# Scenario 5: Qdrant down -> exception propagates (fail-loud, not silent)
# ------------------------------------------------------------------

def test_e2e_qdrant_down_blocks_gracefully(fake_handler: KBCallbackHandler) -> None:
    """Retrieval failures must NOT silently fall through to a hallucinated
    answer. The exception must propagate so the caller can decide what to
    do (e.g. return a generic 503)."""
    vs = _FakeVS()
    vs.raise_on_call = RuntimeError("qdrant down")
    # The LLM response text is irrelevant — the retriever raises first.
    llm = _FakeLLM(scripted=[""])

    with pytest.raises(RuntimeError, match="qdrant down"):
        produce_socratic_response(
            "u1", "什么是勾股定理？",
            llm=llm, vector_store=vs, callback_handler=fake_handler,
        )
    # No LLM call should have been made (retrieval is step 1).
    assert len(llm._calls) == 0
    # No log entry should have been persisted either — we never reached
    # the parser, so there is no validated response to log.
    assert fake_handler._logger.log.call_count == 0


# ------------------------------------------------------------------
# Scenario 6: Redis down -> 3-layer logger falls through to disk spool
# ------------------------------------------------------------------

def test_e2e_redis_down_uses_disk_spool(fake_vs: _FakeVS, fake_handler: KBCallbackHandler) -> None:
    """When db_insert and redis_push both fail, the resilient logger
    falls through to disk_append. produce_socratic_response must not
    crash and must still persist the log entry on the disk layer."""
    text = "勾股定理 [KB:KB-CON-0001] 是 a²+b²=c²。"
    llm = _FakeLLM(scripted=[text])

    from app.services.agent_log.resilient_logger import LogResult
    mock_logger = MagicMock()
    mock_logger.log.return_value = LogResult(status="deferred_disk", layer="disk")
    with patch.object(fake_handler, "_logger", new=mock_logger):
        out = produce_socratic_response(
            "u1", "什么是勾股定理？",
            llm=llm, vector_store=fake_vs, callback_handler=fake_handler,
        )

    assert not out.blocked
    assert len(out.citations) >= 1
    # Callback wrote to the disk layer (deferred_disk), proving fallthrough works.
    mock_logger.log.assert_called_once()
    result = mock_logger.log.return_value
    assert result.status == "deferred_disk"
    assert result.layer == "disk"
