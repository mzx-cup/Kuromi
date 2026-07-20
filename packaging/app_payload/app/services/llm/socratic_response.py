"""End-to-end Socratic response production with anti-hallucination guard.

Pipeline: KB retrieval -> system-prompt injection -> LLM stream -> parse+retry -> log persist.

This is the S3.3 integration module. It does NOT modify ``agents.py`` —
that file is 1600+ lines and touches many unrelated classes. Instead, the
behavior below is exposed as a single ``produce_socratic_response``
function that future slices (S9, S12) can wire into the
``SocraticEvaluatorAgent.handle_user_message`` flow.

Failures observed by the e2e tests:
  * Vector store unavailable  -> retriever raises; this propagates so the
    caller can decide (we do NOT silently return an unbacked answer).
  * Empty / unbacked / invalid LLM output -> caught by the parser +
    ``parse_with_retry`` and either retried once or blocked (with
    ``block_reason``).
  * Callback handler persistence -> resilient 3-layer logger; disk is
    the last-resort durable layer, never raises.
"""
from __future__ import annotations

from typing import List

from langchain_core.messages import HumanMessage

from app.services.callbacks.kb_callback_handler import KBCallbackHandler
from app.services.kb.citation_retriever import CitationHit, CitationRetriever
from app.services.llm.anti_hallucination_parser import (
    AntiHallucinationOutputParser,
    ValidatedResponse,
)
from app.services.llm.retry_strategy import parse_with_retry
from app.services.llm.xunfei_chat_model import XunfeiChatModel


def _format_hits(hits: List[CitationHit]) -> str:
    """Render KB hits as a compact reference section for the system prompt."""
    if not hits:
        return "(no KB hits available)"
    lines = ["## KB Reference Material (cite as [KB:<node_id>])"]
    for h in hits:
        # Cap the snippet so the prompt stays bounded; the LLM doesn't
        # need the full document to know it can cite it.
        snippet = (h.content or "")[:200]
        lines.append(f"- [{h.node_id}] {h.title}: {snippet}")
    return "\n".join(lines)


def _build_socratic_system_prompt(hits: List[CitationHit]) -> str:
    """Socratic evaluator prompt + KB reference material injected verbatim.

    The instruction explicitly warns the LLM to refuse rather than guess
    when no suitable citation exists — this is the Socratic teacher's
    honest "I don't know" behavior the anti-hallucination guard enforces.
    """
    return (
        "你是一位精通苏格拉底教学法的导师。回答学生问题时，必须为每条 claim "
        "提供 [KB:<node_id>] 引用（来自下方参考材料）。如果没有合适的引用，"
        "宁可说「我需要核实一下再回答」，也不要凭空作答。\n\n"
        f"{_format_hits(hits)}"
    )


def _stream_to_text(llm: XunfeiChatModel, messages: list) -> str:
    """Run the streaming LLM and concatenate token content into a single string.

    Chunks are ``ChatGenerationChunk`` whose ``.message`` is an
    ``AIMessageChunk(content=token)``. We do not call ``chunk.content``
    directly because the base ``ChatGenerationChunk`` has no ``content``
    attribute in langchain_core >= 0.3.
    """
    chunks = llm._stream(messages)
    return "".join(c.message.content for c in chunks)


def produce_socratic_response(
    user_id: str,
    message: str,
    *,
    llm: XunfeiChatModel,
    vector_store: object,
    callback_handler: KBCallbackHandler | None = None,
) -> ValidatedResponse:
    """Produce a validated Socratic response for ``message``.

    Returns a ``ValidatedResponse`` (possibly blocked) and persists it via
    the callback handler if one is provided. ``user_id`` is accepted for
    symmetry / future logging hooks — the callback handler carries its
    own ``user_id`` for now.

    Raises whatever the retriever raises (e.g. ``RuntimeError`` when
    Qdrant is down). We deliberately do not catch and return a clean
    blocked response — the security invariant is that retrieval failures
    are LOUD, never silently degraded to a hallucinated answer.
    """
    # 1. Retrieve KB hits. Failures here propagate (fail-loud contract).
    hits = CitationRetriever(vector_store=vector_store).retrieve(message, top_k=5)
    valid_ids = {h.node_id for h in hits}

    # 2. Build parser + retry closure. The closure captures ``llm`` so the
    # retry path uses the exact same streaming entry point as the first
    # attempt — keeps the production code path symmetric.
    parser = AntiHallucinationOutputParser(valid_node_ids=valid_ids)

    def _llm_call(retry_prompt: str) -> str:
        return _stream_to_text(llm, [HumanMessage(content=retry_prompt)])

    # 3. First attempt + retry (via parse_with_retry).
    sys_prompt = _build_socratic_system_prompt(hits)
    first_prompt = sys_prompt + "\n\nUser: " + message
    raw = _llm_call(first_prompt)
    out = parse_with_retry(parser, raw, llm_call=_llm_call)

    # 4. Persist via callback if provided. The callback handler writes
    # through the 3-layer resilient logger and never raises on layer
    # failures — the caller's response is independent of log status.
    if callback_handler is not None:
        callback_handler.on_validated_response(
            output_text=out.text,
            citations=[{"kb_node_id": c.kb_node_id, "claim": c.claim} for c in out.citations],
            risk=out.risk,
            blocked=out.blocked,
            block_reason=out.block_reason,
        )

    return out
