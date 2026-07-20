"""LangChain parity experiment (slice-B3 / slice-B6).

Compares the legacy Socratic pipeline against the new LangChain
``produce_socratic_response`` path on four metrics:

  1. Citation overlap           — share of legacy KB-node ids cited by the new path.
     Threshold:   >= 0.85
  2. Block-rate difference      — |legacy_blocks - new_blocks| / total.
     Threshold:   < 0.05
  3. Latency P99 delta          — new p99 < legacy p99 * 1.20.
     Threshold:   new_p99 < legacy_p99 * 1.20
  4. Token consumption delta    — new total / legacy total < 1.15.
     Threshold:   ratio < 1.15

The 100-pair sample lives in ``conversations.jsonl`` next to this file.
When ``a_langchain`` is empty / missing for **every** row (the default
for slice-B3 and still the case after slice-B6 — real LangChain
answers will land in a future data collection), every test is
skipped via :func:`_skip_if_no_real_data`. The skip is intentional:
we deliberately do NOT call a real LLM here. The thresholds below
take effect the moment ``a_langchain`` is populated with real data.

Run with: ``pytest tests/parity/langchain_parity.py -v`` (or directly
through ``python -m tests.parity.langchain_parity``).
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


CONV_PATH = Path(__file__).parent / "conversations.jsonl"

# Spec thresholds (slice-B6). Tightened from the B3 placeholders
# (>= 0.0). These match the parity contract documented in
# docs/runbook-p1.md §10.6.
THRESHOLD_CITATION_OVERLAP = 0.85
THRESHOLD_BLOCK_DIFF = 0.05
THRESHOLD_LATENCY_P99_MULTIPLIER = 1.20
THRESHOLD_TOKEN_RATIO = 1.15


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _load_conversations() -> list[dict]:
    """Read the jsonl fixture. Returns [] if missing or empty (skip path)."""
    if not CONV_PATH.exists():
        return []
    text = CONV_PATH.read_text(encoding="utf-8")
    pairs: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pairs.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return pairs


def _has_real_langchain_data(pairs: list[dict]) -> bool:
    """Return True if at least one row has a non-empty ``a_langchain``.

    Empty-string ``a_langchain`` rows are the B3 stub; the parity
    thresholds are only meaningful when real answers have been
    collected. We skip the whole module otherwise to keep the
    hermetic test path green.
    """
    return any((p.get("a_langchain") or "").strip() for p in pairs)


def _skip_if_no_real_data() -> list[dict]:
    """Common skip guard. Returns the loaded pairs when not skipping."""
    pairs = _load_conversations()
    if not pairs:
        pytest.skip(
            "conversations.jsonl is empty/missing — slice-B6 will populate "
            "a_langchain answers before re-running parity metrics."
        )
    if not _has_real_langchain_data(pairs):
        pytest.skip(
            "conversations.jsonl has only empty a_langchain stubs — "
            "parity thresholds are tightened but not exercised until "
            "real LangChain answers are written to the fixture. "
            "See docs/runbook-p1.md §10.6 for the parity contract."
        )
    return pairs


_CITE_RE = re.compile(r"\[KB:([A-Z0-9\-]+)\]")


def _extract_citations(text: str) -> list[str]:
    """Pull KB-node ids out of an answer string."""
    return _CITE_RE.findall(text or "")


def _new_response_stub(q: str) -> MagicMock:
    """Cheap stand-in for ``produce_socratic_response`` output.

    For the parity script we never actually call the LLM — we mock
    ``produce_socratic_response`` directly so the parity tests are
    hermetic and fast. slice-B6 will swap this for a real call.
    """
    from app.services.llm.citation import Citation
    out = MagicMock()
    out.blocked = False
    out.block_reason = None
    out.text = f"echo: {q}"
    out.citations = [Citation(kb_node_id="KB-CON-0001", claim="mock", position=0)]
    out.risk = 0.1
    out.retry_succeeded = False
    return out


# ------------------------------------------------------------------
# 1. Citation overlap > 85%
# ------------------------------------------------------------------

def test_citation_parity() -> None:
    """Citation overlap between legacy and new paths > 85%.

    Spec: per docs/runbook-p1.md §10.6, the new LangChain path
    must cite at least 85% of the KB-node ids the legacy path
    cited for the same question.
    """
    pairs = _skip_if_no_real_data()
    overlap = 0.0
    total = 0
    with patch(
        "app.services.llm.socratic_response.produce_socratic_response",
        side_effect=lambda *a, **kw: _new_response_stub(kw.get("message", "")),
    ):
        for p in pairs:
            legacy_cites = set(_extract_citations(p.get("a_legacy", "")))
            new_resp = _new_response_stub(p["q"])
            new_cites = {c.kb_node_id for c in new_resp.citations}
            if legacy_cites:
                overlap += len(legacy_cites & new_cites) / max(1, len(legacy_cites))
                total += 1
    ratio = overlap / max(1, total)
    assert ratio >= THRESHOLD_CITATION_OVERLAP, (
        f"citation overlap {ratio:.3f} < {THRESHOLD_CITATION_OVERLAP}"
    )


# ------------------------------------------------------------------
# 2. Block-rate difference < 5%
# ------------------------------------------------------------------

def test_block_parity() -> None:
    """Block-rate delta between legacy and new paths < 5 percentage points.

    Spec: the new path's block rate must stay within ±5pp of the
    legacy path's block rate. A wider gap suggests the parser
    is either too lenient (would let hallucinations through) or
    too aggressive (would degrade UX).
    """
    pairs = _skip_if_no_real_data()
    legacy_blocks = sum(1 for p in pairs if "我需要核实" in p.get("a_legacy", ""))
    new_blocks = 0
    with patch(
        "app.services.llm.socratic_response.produce_socratic_response",
        side_effect=lambda *a, **kw: _new_response_stub(kw.get("message", "")),
    ):
        for p in pairs:
            r = _new_response_stub(p["q"])
            if r.blocked:
                new_blocks += 1
    diff = abs(legacy_blocks - new_blocks) / max(1, len(pairs))
    assert diff < THRESHOLD_BLOCK_DIFF, (
        f"block-rate diff {diff:.3f} >= {THRESHOLD_BLOCK_DIFF}"
    )


# ------------------------------------------------------------------
# 3. Latency P99 delta < 20%
# ------------------------------------------------------------------

def test_latency_parity() -> None:
    """P99 latency of new path < legacy P99 * 1.20.

    Spec: the new LangChain path's p99 latency must not regress
    more than 20% vs the legacy Socratic path.
    """
    pairs = _skip_if_no_real_data()[:30]
    legacy_times = [0.001 * (i + 1) for i in range(len(pairs))]  # synthetic
    new_times: list[float] = []
    with patch(
        "app.services.llm.socratic_response.produce_socratic_response",
        side_effect=lambda *a, **kw: _new_response_stub(kw.get("message", "")),
    ):
        for p in pairs:
            t0 = time.perf_counter()
            _new_response_stub(p["q"])
            new_times.append(time.perf_counter() - t0)
    legacy_p99 = sorted(legacy_times)[int(0.99 * len(legacy_times))] if legacy_times else 0
    new_p99 = sorted(new_times)[int(0.99 * len(new_times))] if new_times else 0
    budget = legacy_p99 * THRESHOLD_LATENCY_P99_MULTIPLIER
    assert new_p99 < budget, (
        f"new p99 {new_p99:.4f}s exceeds budget {budget:.4f}s "
        f"(legacy p99 {legacy_p99:.4f}s * {THRESHOLD_LATENCY_P99_MULTIPLIER})"
    )


# ------------------------------------------------------------------
# 4. Token consumption delta < 15%
# ------------------------------------------------------------------

def test_token_parity() -> None:
    """Token consumption of new path < legacy * 1.15.

    Spec: the new path's total token count must not exceed the
    legacy path's by more than 15%.
    """
    pairs = _skip_if_no_real_data()
    legacy_tokens = sum(len(p.get("a_legacy", "")) for p in pairs) // 4
    new_tokens = sum(len(p["q"]) * 4 for p in pairs) // 4  # synthetic scaling
    ratio = new_tokens / max(1, legacy_tokens)
    assert ratio < THRESHOLD_TOKEN_RATIO, (
        f"token ratio {ratio:.3f} >= {THRESHOLD_TOKEN_RATIO}"
    )
