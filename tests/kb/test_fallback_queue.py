"""Tests for KB Qdrant fallback queue (MEDIUM-3).

验证:
  - enqueue_kb_fallback 写入 JSONL 文件
  - drain_pending 返回队列内容并清空
  - 队列满（> 1000）时丢弃最旧条目（FIFO）
  - 文件不存在时不崩
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_queue_dir(monkeypatch):
    """临时目录用于 fallback queue 文件。"""
    d = tempfile.mkdtemp()
    queue_file = Path(d) / "kb_fallback.jsonl"
    monkeypatch.setattr("app.services.kb.fallback_queue._FALLBACK_FILE", queue_file)
    yield queue_file
    shutil.rmtree(d, ignore_errors=True)


def test_enqueue_writes_to_jsonl(temp_queue_dir):
    """enqueue 必须写入 JSONL 文件。"""
    from app.services.kb.fallback_queue import enqueue_kb_fallback

    enqueue_kb_fallback(
        node_id="n_1", subject="math", title="勾股定理", content="a²+b²=c²"
    )
    assert temp_queue_dir.exists()
    lines = temp_queue_dir.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj["node_id"] == "n_1"
    assert obj["subject"] == "math"


def test_multiple_enqueues_accumulate(temp_queue_dir):
    """多次 enqueue 必须累积（追加模式）。"""
    from app.services.kb.fallback_queue import enqueue_kb_fallback

    for i in range(3):
        enqueue_kb_fallback(node_id=f"n_{i}", subject="s", title="t", content="c")
    lines = temp_queue_dir.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3


def test_drain_pending_returns_and_clears(temp_queue_dir):
    """drain_pending 必须返回所有 pending 条目并清空文件。"""
    from app.services.kb.fallback_queue import (
        drain_pending,
        enqueue_kb_fallback,
    )

    enqueue_kb_fallback("n_1", "s", "t", "c")
    enqueue_kb_fallback("n_2", "s", "t", "c")

    pending = drain_pending()
    assert len(pending) == 2
    assert pending[0]["node_id"] == "n_1"
    assert pending[1]["node_id"] == "n_2"

    # 文件必须被清空（移到 .processed）
    processed = temp_queue_dir.with_suffix(".jsonl.processed")
    assert processed.exists()
    assert not temp_queue_dir.exists() or temp_queue_dir.stat().st_size == 0


def test_drain_pending_empty_queue(temp_queue_dir):
    """空队列 drain 必须返回空 list（不崩）。"""
    from app.services.kb.fallback_queue import drain_pending

    pending = drain_pending()
    assert pending == []


def test_queue_size_cap_drops_oldest(temp_queue_dir):
    """超过 MAX_QUEUE_SIZE 时必须丢弃最旧条目（FIFO）。"""
    from app.services.kb import fallback_queue as fq_mod

    # 用一个较小的 cap 便于测试
    original_max = fq_mod.MAX_QUEUE_SIZE
    fq_mod.MAX_QUEUE_SIZE = 5
    try:
        for i in range(10):
            fq_mod.enqueue_kb_fallback(node_id=f"n_{i:02d}", subject="s", title="t", content="c")
        # 只保留最后 5 条
        pending = fq_mod.drain_pending()
        assert len(pending) == 5
        assert pending[0]["node_id"] == "n_05"
        assert pending[-1]["node_id"] == "n_09"
    finally:
        fq_mod.MAX_QUEUE_SIZE = original_max


def test_enqueue_handles_missing_directory(temp_queue_dir, monkeypatch):
    """目录不存在时必须自动创建。"""
    # 重定向到不存在的子目录
    nested = temp_queue_dir.parent / "nested" / "kb.jsonl"
    monkeypatch.setattr("app.services.kb.fallback_queue._FALLBACK_FILE", nested)
    from app.services.kb.fallback_queue import enqueue_kb_fallback

    enqueue_kb_fallback("n_x", "s", "t", "c")
    assert nested.exists()