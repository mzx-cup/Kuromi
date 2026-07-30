"""OrchestratorChain: 任意 Agent → 任意 Agent 的链式重试 + 共识投票（M2.4）

设计要点：
  - 每个 ChainLink 是一个 async callable，签名 (state: dict) -> dict
  - 失败时按 backoff_seconds * attempt 退避重试，超过 max_retries 终止链
  - 返回 ChainResult 包含 success、最终 state、错误列表、执行过的 link 名

使用示例:
    chain = OrchestratorChain([
        ChainLink(name="audit", fn=audit_agent.run, max_retries=2),
        ChainLink(name="recommend", fn=recommend_agent.run),
    ])
    result = await chain.run({"user_id": "u1", "input": "..."})
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

logger = logging.getLogger("starlearn.orchestrator.chain")

ChainFn = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass
class ChainLink:
    """链中的一个节点：name + async fn + 失败重试策略。"""

    name: str
    fn: ChainFn
    max_retries: int = 0
    backoff_seconds: float = 0.0  # M2 默认 0；M3 可配置


@dataclass
class ChainResult:
    """链执行的最终结果。"""

    success: bool
    state: dict[str, Any]
    errors: list[str] = field(default_factory=list)
    links_executed: list[str] = field(default_factory=list)


class OrchestratorChain:
    """可编排的多 Agent 链路。"""

    def __init__(self, links: list[ChainLink]) -> None:
        if not links:
            raise ValueError("OrchestratorChain requires at least one link")
        self._links = links

    async def run(self, initial_state: dict[str, Any]) -> ChainResult:
        state = dict(initial_state)
        errors: list[str] = []
        executed: list[str] = []

        for link in self._links:
            attempt = 0
            while attempt <= link.max_retries:
                try:
                    state = await link.fn(state)
                    executed.append(link.name)
                    break
                except Exception as exc:  # noqa: BLE001
                    attempt += 1
                    if attempt > link.max_retries:
                        msg = f"{link.name} failed after {attempt - 1} retries: {exc}"
                        logger.error(msg)
                        errors.append(msg)
                        return ChainResult(
                            success=False,
                            state=state,
                            errors=errors,
                            links_executed=executed,
                        )
                    if link.backoff_seconds > 0:
                        await asyncio.sleep(link.backoff_seconds * attempt)

        return ChainResult(success=True, state=state, errors=errors, links_executed=executed)