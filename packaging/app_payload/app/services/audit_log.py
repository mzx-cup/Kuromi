# -*- coding: utf-8 -*-
"""JSON Lines 审计日志 — Phase 1 L0/L3 管线专用。

写入 `storage/audit.log`,每行一条 JSON 记录。失败时**不抛异常**(审计失败不阻塞业务)。
本期不切分/不轮转,留待下一期补 rotate。
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_DIR = Path(__file__).resolve().parents[2] / "storage"
_DEFAULT_FILE = _DEFAULT_DIR / "audit.log"

_write_lock = Lock()


def _resolve_path() -> Path:
    """允许通过环境变量 XINSHI_AUDIT_LOG 覆盖路径(测试时常用 tmp 目录)。"""
    override = os.environ.get("XINSHI_AUDIT_LOG")
    if override:
        return Path(override)
    return _DEFAULT_FILE


def _append(record: dict[str, Any]) -> None:
    path = _resolve_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _write_lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception as e:  # noqa: BLE001 — 审计失败不抛
        logger.warning("[audit_log] 写入失败: %s (path=%s)", e, path)


def audit_input_block(student_id: str, code: str, snippet: str) -> None:
    """L0 拦截用户输入时记录。snippet 已截断 ≤200 字符,不存原文。"""
    _append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": "input_block",
        "student_id": str(student_id)[:64],
        "code": code,
        "snippet": (snippet or "")[:200],
    })


def audit_output_replace(student_id: str, code: str, count: int = 1) -> None:
    """L3 输出脱敏/截断时记录。**不**存原文,只记类型与次数。"""
    _append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": "output_replace",
        "student_id": str(student_id)[:64],
        "code": code,
        "count": int(count),
    })


def audit_intent_route(student_id: str, intent: str) -> None:
    """L1 意图路由结果(可选打点)。"""
    _append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": "intent_route",
        "student_id": str(student_id)[:64],
        "intent": intent,
    })
