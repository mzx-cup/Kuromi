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


# ============================================================
# 扩展:Agent 决策审计(v2.0 P0 全链路可审计日志)
# ============================================================

def audit_agent_decision(
    student_id: str,
    agent_id: str,
    action: str,
    *,
    trace_id: str | None = None,
    input_summary: str | None = None,
    output_summary: str | None = None,
    reasoning: str | None = None,
    knowledge_sources: list[str] | None = None,
    confidence: float | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """记录单个 Agent 的决策过程(v2.0 全链路可审计日志补全).

    Args:
        student_id: 学生 ID(截断到 64 字符)
        agent_id: Agent 标识(echo / profiler / planner / evaluator ...)
        action: 决策动作(recommend / grade / push / generate ...)
        trace_id: 链路追踪 ID
        input_summary: 输入摘要(**不存原文**,只存摘要)
        output_summary: 输出摘要(**不存原文**)
        reasoning: 决策理由(让审计者能复盘"为什么这么决策")
        knowledge_sources: 引用的知识源 ID 列表(如 KB 节点 ID)
        confidence: 置信度 0-1(可选)
        extra: 其它需要留痕的字段
    """
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": "agent_decision",
        "student_id": str(student_id)[:64],
        "agent_id": str(agent_id)[:64],
        "action": str(action)[:128],
    }
    if trace_id:
        record["trace_id"] = str(trace_id)[:64]
    if input_summary is not None:
        record["input_summary"] = (input_summary or "")[:200]
    if output_summary is not None:
        record["output_summary"] = (output_summary or "")[:200]
    if reasoning is not None:
        record["reasoning"] = (reasoning or "")[:500]
    if knowledge_sources:
        # 只保留 ID,不存原文
        record["knowledge_sources"] = [str(s)[:64] for s in knowledge_sources[:20]]
    if confidence is not None:
        try:
            c = float(confidence)
            if 0.0 <= c <= 1.0:
                record["confidence"] = round(c, 3)
        except (TypeError, ValueError):
            pass
    if extra:
        # extra 限定大小,避免审计日志爆炸
        record["extra"] = {str(k)[:32]: str(v)[:200] for k, v in extra.items()}
    _append(record)


def audit_pipeline_complete(
    student_id: str,
    trace_id: str,
    agents_run: list[str],
    *,
    duration_ms: int | None = None,
    status: str = "complete",
    error: str | None = None,
) -> None:
    """记录一次完整流水线执行(用于回溯沙箱的数据源)."""
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": "pipeline_complete",
        "student_id": str(student_id)[:64],
        "trace_id": str(trace_id)[:64],
        "agents_run": [str(a)[:64] for a in agents_run[:32]],
        "status": str(status)[:32],
    }
    if duration_ms is not None:
        try:
            record["duration_ms"] = int(duration_ms)
        except (TypeError, ValueError):
            pass
    if error:
        record["error"] = str(error)[:300]
    _append(record)


def audit_jailbreak_attempt(
    student_id: str,
    pattern_matched: str,
    snippet: str,
    *,
    classifier_intent: str | None = None,
    classifier_confidence: float | None = None,
) -> None:
    """记录越狱/注入尝试(用于安全审计 + 越狱样本积累).

    Args:
        student_id: 学生 ID
        pattern_matched: 命中的规则 code(PROMPT_INJECTION / DESTRUCTIVE / ...)
        snippet: 输入片段(已截断)
        classifier_intent: 意图分类器的判定(normal / injection / role_escape / overreach)
        classifier_confidence: 意图分类器置信度
    """
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": "jailbreak_attempt",
        "student_id": str(student_id)[:64],
        "pattern_matched": str(pattern_matched)[:64],
        "snippet": (snippet or "")[:200],
    }
    if classifier_intent:
        record["classifier_intent"] = str(classifier_intent)[:32]
    if classifier_confidence is not None:
        try:
            record["classifier_confidence"] = round(float(classifier_confidence), 3)
        except (TypeError, ValueError):
            pass
    _append(record)
