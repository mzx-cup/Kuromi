# -*- coding: utf-8 -*-
"""智能体统一 I/O 结构 (AgentEnvelope).

设计动机:
  6 层架构中, 智能体层之间只能通过结构化 Envelope 通信. 每个 Envelope 至少包含:
    - trace_id: 全链路唯一 ID, 用于跨智能体串联 (与 LivePathResult.trace_id 共享)
    - role: 智能体角色 (AgentRole)
    - payload: 业务数据, 形态由各 Agent 自行定义, 但必须是 dict
    - latency_ms: 本次调用耗时
    - fallback: 是否降级 (True 表示 LLM/KB 等不可用, 走种子响应)
    - provider: 调用来源 (e.g. "ark", "qwen", "human") — 便于答辩时回溯
    - error: 失败原因 (fallback=True 时必填)

序列化:
  - to_json / from_json: 用于跨进程/跨服务传递, 含 Enum 兼容
  - 等值比较通过 dataclass 默认 __eq__ 完成

使用样例:
    >>> from app.agents.io_schema import AgentEnvelope, AgentRole
    >>> env = AgentEnvelope(trace_id="t1", role=AgentRole.SOCRATIC, payload={"q": "hi"})
    >>> env.to_json()
    '{"trace_id": "t1", "role": "socratic", "payload": {"q": "hi"}, ...}'
"""
from __future__ import annotations

import enum
import json
from dataclasses import asdict, dataclass, field
from typing import Any


class AgentRole(str, enum.Enum):
    """智能体角色枚举. 与设计文档 6 层架构中的智能体层一一对应."""

    PROFILER = "profiler"
    PLANNER = "planner"
    SOCRATIC = "socratic"
    RECOMMEND = "recommend"
    CRITIC = "critic"
    AUDIT = "audit"


@dataclass
class AgentEnvelope:
    """智能体 I/O 统一结构."""

    trace_id: str
    role: AgentRole
    payload: dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0
    fallback: bool = False
    provider: str = ""
    error: str = ""

    def to_json(self) -> str:
        d = asdict(self)
        d["role"] = self.role.value
        return json.dumps(d, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "AgentEnvelope":
        d = json.loads(raw)
        d["role"] = AgentRole(d["role"])
        return cls(**d)


# ============================================================
# P1 Task 13 完成: wrap_agent_call — 智能体调用装饰器/包装器
#
# 设计动机:
#   6 层架构中, 智能体之间只通过 Envelope 通信. 现有 agents.py 中
#   各 Agent.run() 仍然是同步/异步函数调用, 没有 trace_id 串联, 也没有
#   fallback 标记. 这个 wrap_agent_call 工具**不修改 agents.py 任何一行**,
#   由调用方 (P1 阶段 main.py / api 路由) 选择性使用:
#
#       result_envelope = await wrap_agent_call(
#           AgentRole.PLANNER,
#           planner_agent.run,
#           state, **kwargs,
#       )
#
# 行为契约:
#   1. 生成 trace_id = "ag_<10hex>" (与 LivePathResult 的 "lp_" 区别)
#   2. 调用 fn(*args, **kwargs), 计时 (latency_ms)
#   3. 若返回 dict, 包成 payload; 否则包成 {"result": ret}
#   4. 若抛异常, 标记 fallback=True, error=str(exc), 不重抛
#
# 注意: 这是**辅助工具**, 不是强制包装. P1 阶段会把所有 run() 调用点
#       切到 wrap_agent_call; P0 阶段不切, 保持零修改.
# ============================================================
import time
import uuid  # noqa: E402  (放在模块末尾, 避免重构时挪动位置)


async def wrap_agent_call(
    role: AgentRole,
    fn: Callable[..., Any],
    *args: Any,
    trace_id: str | None = None,
    provider: str = "",
    **kwargs: Any,
) -> AgentEnvelope:
    """包装智能体调用, 返回 AgentEnvelope.

    Args:
        role: 智能体角色 (AgentRole 枚举).
        fn: 被调用的可执行对象 (coroutine function / 普通函数 / 方法).
        *args: 透传给 fn 的位置参数.
        trace_id: 可选, 显式传入 trace_id; 默认自动生成 ag_<10hex>.
        provider: 调用来源 (e.g. "ark"/"qwen"/"human"), 用于答辩回溯.
        **kwargs: 透传给 fn 的关键字参数.

    Returns:
        AgentEnvelope: 包含 trace_id / role / payload / latency_ms / fallback / provider / error.
        失败时**不抛异常**, 而是返回 fallback=True 的 Envelope, 便于上层主链不断.
    """
    tid = trace_id or f"ag_{uuid.uuid4().hex[:10]}"
    t0 = time.time()
    try:
        out = fn(*args, **kwargs)
        # 若 fn 是 async 协程函数, 实际 await 在这里发生
        if asyncio.iscoroutine(out):
            out = await out
        latency_ms = int((time.time() - t0) * 1000)
        if isinstance(out, AgentEnvelope):
            # 若 fn 自身已返回 Envelope, 保留其字段但覆盖 trace_id 与 role
            out.trace_id = out.trace_id or tid
            out.role = role
            if latency_ms:
                out.latency_ms = latency_ms
            if provider and not out.provider:
                out.provider = provider
            return out
        payload = out if isinstance(out, dict) else {"result": out}
        return AgentEnvelope(
            trace_id=tid,
            role=role,
            payload=payload,
            latency_ms=latency_ms,
            fallback=False,
            provider=provider,
        )
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.time() - t0) * 1000)
        return AgentEnvelope(
            trace_id=tid,
            role=role,
            payload={},
            latency_ms=latency_ms,
            fallback=True,
            provider=provider,
            error=str(exc),
        )


import asyncio  # noqa: E402  (放在 wrap_agent_call 内用到后再 import, 减少启动期负担)
from typing import Callable  # noqa: E402
