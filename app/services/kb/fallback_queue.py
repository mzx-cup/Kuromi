"""KB Qdrant Fallback Queue（MEDIUM-3 修复）

当 Qdrant upsert 失败时（连接超时 / collection 不存在 / OOM），不再只 log 丢弃，
而是把失败任务追加到 JSONL 文件，异步 worker 可以 replay 重新 upsert。

数据流：
  1. _persist_to_qdrant() 失败 → enqueue_kb_fallback()
  2. 后台 worker（未来 M6+）定期 drain_pending() 并重试 upsert
  3. 处理完成后 drain_pending 把文件 move 到 .processed

生产部署：
  - JSONL 文件位于 /var/log/starlearn/kb_fallback.jsonl（容器外挂卷）
  - worker 用 inotify / cron 触发
"""
from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("starlearn.kb.fallback_queue")

# 默认 JSONL 文件路径（测试时通过 monkeypatch 覆盖）
_FALLBACK_FILE = Path("/tmp/starlearn_kb_fallback.jsonl")

# 单文件最大条目数；超过则丢弃最旧（FIFO）
MAX_QUEUE_SIZE = 1000


def enqueue_kb_fallback(
    node_id: str,
    subject: str,
    title: str,
    content: str,
) -> None:
    """把 Qdrant 写入失败的任务加入 fallback 队列。"""
    record = {
        "node_id": node_id,
        "subject": subject,
        "title": title,
        "content": content,
        "enqueued_at": datetime.utcnow().isoformat(),
    }
    try:
        _FALLBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        # 写入新条目
        with _FALLBACK_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        # 裁剪：如果超过 MAX_QUEUE_SIZE，丢弃最旧的
        _trim_queue_if_oversize()
        logger.info(f"KB fallback enqueued: {node_id}")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"KB fallback enqueue failed for {node_id}: {exc}")


def drain_pending() -> list[dict]:
    """取出所有 pending 条目并归档。

    Returns:
        list of {node_id, subject, title, content, enqueued_at}

    Side effect:
        原 JSONL 文件被 move 到 `<file>.processed` 防止重复处理。
    """
    if not _FALLBACK_FILE.exists():
        return []

    processed_file = _FALLBACK_FILE.with_suffix(".jsonl.processed")
    try:
        # 先把原文件 move 到 processed（避免新追加丢失）
        shutil.move(str(_FALLBACK_FILE), str(processed_file))
    except FileNotFoundError:
        return []

    pending: list[dict] = []
    try:
        with processed_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    pending.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"Skipping malformed line: {line[:100]!r}")
        logger.info(f"Drained {len(pending)} KB fallback entries")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Failed to read {processed_file}: {exc}")

    return pending


def _trim_queue_if_oversize() -> None:
    """如果队列超过 MAX_QUEUE_SIZE，丢弃最旧的（FIFO）。"""
    if not _FALLBACK_FILE.exists():
        return

    try:
        with _FALLBACK_FILE.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return

    if len(lines) <= MAX_QUEUE_SIZE:
        return

    keep = lines[-MAX_QUEUE_SIZE:]
    with _FALLBACK_FILE.open("w", encoding="utf-8") as f:
        f.writelines(keep)
    logger.warning(
        f"KB fallback queue trimmed: {len(lines)} -> {len(keep)} "
        f"(dropped {len(lines) - len(keep)} oldest)"
    )