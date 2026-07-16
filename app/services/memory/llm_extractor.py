"""LLM-backed pattern extractor for episodic → semantic consolidation (S6.2).

This is the second step of Core Innovation 2: 记忆巩固 (Memory Consolidation).
After ``clustering.py`` groups similar episodic events into clusters, this
module asks an LLM to summarise each cluster into a single declarative
``statement`` (the candidate ``SemanticMemory``), together with a confidence
score and the list of episode ids that ground it. The downstream
``consolidator`` (S6.3) feeds this output into ``reinforce`` / ``weaken``.

The real implementation will call ``XunfeiChatModel`` with ``PROMPT`` and
parse the JSON reply. In S6.2 we ship a deterministic stub so the consolidator
and tests can be built and reviewed before live LLM wiring lands.
"""
from __future__ import annotations

import json
import logging
import signal
import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.services.llm.xunfei_chat_model import XunfeiChatModel

_log = logging.getLogger(__name__)

# Per-cluster wall-clock budget for the live LLM call. On timeout we
# fail open (return a low-confidence fallback) so one slow cluster can't
# stall the whole consolidation pass.
_TIMEOUT_S = 30

PROMPT = """以下是用户 X 的 {n} 条学习事件。请提取 1 条 pattern，JSON 格式：
{{"statement": "<一句陈述>", "confidence": <0-1>, "evidence_ids": [...]}}
"""

PROMPT_VERSION = "v1"

# Validate the format string at import time so a placeholder typo surfaces
# here rather than in the consolidator (S6.3) or the live LLM call.
_ = PROMPT.format(n=1)


@contextmanager
def _signal_timeout(seconds: int):
    """Unix wall-clock timeout via ``SIGALRM`` (main-thread only).

    Matches the S6 plan: the consolidator runs inside APScheduler on the
    main thread, so ``SIGALRM`` fires there. Not available on Windows /
    non-main threads — callers must guard with ``_has_signal_alarm()``.
    """
    def _handler(signum, frame):  # pragma: no cover - fires via alarm
        raise TimeoutError("LLM extract timeout")

    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def _has_signal_alarm() -> bool:
    """True only where ``signal.alarm`` exists and we're on the main thread."""
    return (
        hasattr(signal, "SIGALRM")
        and hasattr(signal, "alarm")
        and threading.current_thread() is threading.main_thread()
    )


def _consume_stream(llm: "XunfeiChatModel", prompt: str) -> str:
    """Drive ``llm._stream`` (a *sync* generator) and concatenate content."""
    chunks = llm._stream([HumanMessage(content=prompt)])
    return "".join(chunk.message.content for chunk in chunks)


def _consume_stream_with_thread_timeout(
    llm: "XunfeiChatModel", prompt: str, seconds: int
) -> str:
    """Cross-platform fallback timeout for hosts without ``SIGALRM``.

    Runs the (blocking) stream consumption on a daemon worker thread and
    waits at most ``seconds``. A slow stream is abandoned (the daemon dies
    with the process) and a ``TimeoutError`` is raised so the caller fails
    open, mirroring the ``SIGALRM`` path's behaviour.
    """
    box: dict = {}

    def _worker() -> None:
        try:
            box["raw"] = _consume_stream(llm, prompt)
        except BaseException as exc:  # noqa: BLE001 - re-raised on join
            box["exc"] = exc

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()
    worker.join(seconds)
    if worker.is_alive():
        raise TimeoutError("LLM extract timeout")
    if "exc" in box:
        raise box["exc"]
    return box.get("raw", "")


def extract_pattern(
    user_id: str,
    cluster: list[dict],
    llm: "XunfeiChatModel | None" = None,
) -> dict:
    """Extract one declarative pattern from a cluster of episodic events.

    If ``llm`` is ``None`` we fall back to the deterministic stub (kept for
    backward compatibility and for tests that don't need a real LLM). When
    an ``llm`` is supplied we format ``PROMPT``, stream the reply under a
    per-cluster wall-clock timeout, and parse the JSON. Any failure
    (timeout, transport error, malformed / non-JSON reply) fails open to a
    low-confidence fallback so a single bad cluster can't abort the pass.

    Args:
        user_id: Owner of the cluster. Injected into the prompt for
            traceability by the real path; unused by the stub.
        cluster: List of episodic event dicts, each with at least an
            ``id`` (str). May be empty.
        llm: Optional ``XunfeiChatModel`` (duck-typed: anything exposing a
            sync ``_stream(messages)`` generator of chunks with
            ``.message.content``). ``None`` selects the legacy stub.

    Returns:
        A dict with keys ``statement`` (str), ``confidence`` (float in
        ``[0.0, 1.0]``), and ``evidence_ids`` (list[str]).
    """
    if not cluster:
        return {"statement": "无事件", "confidence": 0.0, "evidence_ids": []}

    if llm is None:
        # Legacy deterministic stub (S6.2 boundary; drives the pipeline
        # deterministically for tests that don't wire a live LLM).
        n = len(cluster)
        return {
            "statement": f"用户在 {n} 个事件中重复练习相关内容",
            "confidence": 0.7,
            "evidence_ids": [c["id"] for c in cluster],
        }

    fallback = {
        "statement": "无事件",
        "confidence": 0.0,
        "evidence_ids": [c["id"] for c in cluster],
    }

    # Real path: prompt + stream + JSON parse, under a per-cluster timeout.
    prompt = PROMPT.format(n=len(cluster))
    try:
        if _has_signal_alarm():
            with _signal_timeout(_TIMEOUT_S):
                raw = _consume_stream(llm, prompt)
        else:
            raw = _consume_stream_with_thread_timeout(llm, prompt, _TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001 - fail open per cluster
        _log.warning("LLM extract failed (%s), using fallback.", exc)
        return fallback

    try:
        parsed = json.loads(raw.strip())
        if not isinstance(parsed, dict):
            raise ValueError("LLM reply is not a JSON object")
    except (json.JSONDecodeError, ValueError) as exc:
        _log.warning("LLM returned non-object JSON (%s): %r", exc, raw[:200])
        return fallback

    return {
        "statement": str(parsed.get("statement", "无事件"))[:200],
        "confidence": float(parsed.get("confidence", 0.0)),
        "evidence_ids": list(
            parsed.get("evidence_ids", [c["id"] for c in cluster])
        ),
    }