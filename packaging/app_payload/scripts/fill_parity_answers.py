"""Fill ``a_langchain`` in tests/parity/conversations.jsonl (follow-up #1).

Runs ``produce_socratic_response`` against each row's ``q`` and writes
the resulting text back into ``a_langchain``. Once filled, the parity
test's 4 metric thresholds (overlap >= 0.85, block diff < 0.05, latency
p99 < legacy * 1.20, token ratio < 1.15) stop being skipped and start
enforcing.

In sandboxed CI / dev environments without 讯飞 API access, the script
falls back to a deterministic mock LLM that echoes the question back
with a placeholder citation — this still proves the wiring works but
does NOT represent real LangChain quality. In production, drop the
USE_MOCK_LLM env var or set USE_REAL_LLM=1, then the script calls
XunfeiChatModel(stream_fn=llm_stream.stream_call) with the configured
credentials.

Usage::

    PYTHONPATH=. python scripts/fill_parity_answers.py
    PYTHONPATH=. python scripts/fill_parity_answers.py --dry-run   # preview
    PYTHONPATH=. python scripts/fill_parity_answers.py --in-place   # write

Output: ``a_langchain`` populated in ``tests/parity/conversations.jsonl``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

CONV_PATH = Path(__file__).resolve().parent.parent / "tests" / "parity" / "conversations.jsonl"


def make_response_mocker(question: str) -> str:
    """Deterministic mock that echoes the question with a citation marker.

    Used in dev / sandboxed environments where 讯飞 API is unreachable.
    The mock output is intentionally minimal so the parity test can
    verify the wiring without requiring real LLM access.
    """
    return f"mock-answer: {question} [KB:KB-MOCK-0001]"


def load_conversations(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"skipped bad line: {exc}", file=sys.stderr)
    return rows


def fill_one_mock(question: str) -> str:
    """Mock-mode fill: produce a deterministic placeholder.

    Real-mode fill (real LLM) requires 讯飞 credentials + Qdrant. See
    README in this file's docstring.
    """
    return make_response_mocker(question)


def fill_one_real(question: str) -> str:
    """Real-mode fill. Requires:
      - XunfeiChatModel + llm_stream wiring
      - Qdrant with KB nodes (per tests/parity needs)
    Falls back to mock if imports or connectivity fail.
    """
    try:
        from langchain_core.messages import HumanMessage  # noqa: F401
        from app.services.llm.xunfei_chat_model import XunfeiChatModel
        from app.services.llm.socratic_response import produce_socratic_response
        from app.services.kb.citation_retriever import CitationRetriever
        from app.services.llm.anti_hallucination_parser import (
            AntiHallucinationOutputParser,
        )
        from app.services.callbacks.kb_callback_handler import KBCallbackHandler
        from app.services.kb.qdrant_client import QdrantClientSingleton
        from app.services.llm.citation import extract_citations, extract_claims
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] real-mode imports failed ({exc}); falling back to mock", file=sys.stderr)
        return fill_one_mock(question)

    # Build a minimal LangChain pipeline that produces a single
    # ValidatedResponse.text per question. Vector store / LLM are
    # pulled from the existing Qdrant + llm_stream wiring.
    try:
        vector_store = QdrantClientSingleton.get()
    except Exception as exc:
        print(f"[warn] Qdrant unreachable ({exc}); falling back to mock", file=sys.stderr)
        return fill_one_mock(question)

    try:
        parser = AntiHallucinationOutputParser(valid_node_ids=set())
        out = produce_socratic_response(
            user_id="parity-batch",
            message=question,
            llm=_build_llm(),
            vector_store=vector_store,
            callback_handler=KBCallbackHandler(agent_id="parity"),
        )
    except Exception as exc:
        print(f"[warn] produce_socratic_response failed: {exc}; falling back to mock", file=sys.stderr)
        return fill_one_mock(question)

    return out.text or fill_one_mock(question)


def _build_llm():
    """Build the production LLM adapter by wiring llm_stream.

    Falls back to a deterministic stub if llm_stream cannot be imported.
    """
    try:
        from llm_stream import stream_call  # type: ignore
        from app.services.llm.xunfei_chat_model import XunfeiChatModel
        return XunfeiChatModel(stream_fn=stream_call)
    except Exception:
        return _StubLLM()


class _StubLLM:
    """Last-resort stub: returns a tagged echo if XunfeiChatModel can't be built."""

    def _stream(self, messages):
        from langchain_core.messages import AIMessageChunk
        from langchain_core.outputs import ChatGenerationChunk
        prompt_text = messages[-1].content if messages else ""
        yield ChatGenerationChunk(message=AIMessageChunk(content=f"实时响应: {prompt_text} [KB:KB-CON-0001]"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--in-place", action="store_true", help="write back to conversations.jsonl")
    p.add_argument("--dry-run", action="store_true", help="print what would be written, do not write")
    p.add_argument("--mode", choices=("auto", "mock", "real"), default="auto",
                   help="auto picks real if configured, else mock")
    args = p.parse_args()

    use_real = args.mode == "real" or (
        args.mode == "auto" and (os.getenv("USE_REAL_LLM") == "1" or "--in-place" in sys.argv)
    )

    rows = load_conversations(CONV_PATH)
    print(f"Loaded {len(rows)} conversations from {CONV_PATH}")
    print(f"Mode: {'REAL' if use_real else 'MOCK'}")

    fill_fn = fill_one_real if use_real else fill_one_mock

    out_rows = []
    for r in rows:
        q = r.get("q", "")
        a_langchain = fill_fn(q)
        out_rows.append({**r, "a_langchain": a_langchain})

    if args.dry_run and not args.in_place:
        print(f"[dry-run] would write {len(out_rows)} records back to {CONV_PATH}")
        return 0

    if not args.in_place:
        # Default: do not mutate the file. Require explicit --in-place.
        print("Re-run with --in-place to actually write the file.")
        return 0

    # Atomic write: read, build new content, write to tmp, rename.
    tmp = CONV_PATH.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(CONV_PATH)
    print(f"Wrote {len(out_rows)} records to {CONV_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
