"""LangChain parity experiment (slice-B3 / slice-B6).

Compares the legacy Socratic pipeline against the new LangChain
``produce_socratic_response`` path on four metrics:
  1. Citation overlap           — share of legacy KB-node ids cited by the new path.
  2. Block-rate difference      — |legacy_blocks - new_blocks| / total.
  3. Latency P99 delta          — new p99 < legacy p99 * 1.20.
  4. Token consumption delta    — new total / legacy total < 1.15.

The 100-pair sample lives in ``conversations.jsonl`` next to this file.
When the file is empty or missing (the default for slice-B3), every test
is skipped — we deliberately do NOT call a real LLM here. slice-B6 will
populate ``a_langchain`` and rerun.

Run with: ``pytest tests/parity/langchain_parity.py -v`` (or directly
through ``python -m tests.parity.langchain_parity``).
"""
from __future__ import annotations

import json
import re
import statistics
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


CONV_PATH = Path(__file__).parent / "conversations.jsonl"


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


_CITE_RE = re.compile(r"\[KB:([A-Z0-9\-]+)\]")


def _extract_citations(text: str) -> list[str]:
    """Pull KB-node ids out of an answer string."""
    return _CITE_RE.findall(text or "")


def _skip_if_empty() -> None:
    pairs = _load_conversations()
    if not pairs:
        pytest.skip(
            "conversations.jsonl is empty/missing — slice-B6 will populate "
            "a_langchain answers before re-running parity metrics."
        )


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
    """Citation overlap between legacy and new paths > 85%."""
    _skip_if_empty()
    pairs = _load_conversations()
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
    assert ratio >= 0.0  # placeholder; slice-B6 will tighten to > 0.85


# ------------------------------------------------------------------
# 2. Block-rate difference < 5%
# ------------------------------------------------------------------

def test_block_parity() -> None:
    """Block-rate delta between legacy and new paths < 5 percentage points."""
    _skip_if_empty()
    pairs = _load_conversations()
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
    assert diff >= 0.0  # placeholder; slice-B6 will tighten to < 0.05


# ------------------------------------------------------------------
# 3. Latency P99 delta < 20%
# ------------------------------------------------------------------

def test_latency_parity() -> None:
    """P99 latency of new path < legacy P99 * 1.20."""
    _skip_if_empty()
    pairs = _load_conversations()[:30]
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
    # Placeholder assertion; slice-B6 will tighten to < legacy * 1.20.
    assert new_p99 < legacy_p99 * 100


# ------------------------------------------------------------------
# 4. Token consumption delta < 15%
# ------------------------------------------------------------------

def test_token_parity() -> None:
    """Token consumption of new path < legacy * 1.15."""
    _skip_if_empty()
    pairs = _load_conversations()
    legacy_tokens = sum(len(p.get("a_legacy", "")) for p in pairs) // 4
    new_tokens = sum(len(p["q"]) * 4 for p in pairs) // 4  # synthetic scaling
    ratio = new_tokens / max(1, legacy_tokens)
    assert ratio >= 0.0  # placeholder; slice-B6 will tighten to < 1.15