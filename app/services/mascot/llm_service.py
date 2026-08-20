# -*- coding: utf-8 -*-
"""
小星 AI 学习助手 → MiniMax 大模型 API 接入层。

设计目标
--------
- 直接调用 ``llm_stream.call_llm_stream_messages``，使用项目已配置好的
  MiniMax (``minimax-Text-01``) Chat Completions 接口；
- 使用 ``app/api/mascot.py`` 中的 ``MASCOT_SYSTEM_PROMPT`` 作为系统 prompt，
  注入 ``page_context`` / ``user_profile`` / ``today_stats`` 上下文；
- 拼接前端传入的 ``conversation_history`` 还原多轮对话；
- 支持按请求参数覆盖 ``model`` 和 ``temperature``（默认沿用
  ``settings.minimax_model_name`` 与 ``MASCOT_DEFAULT_TEMPERATURE``）；
- 暴露统一的 ``AsyncGenerator[str, None]`` 接口给上层 SSE endpoint 使用。

不变量
------
- 与 ``MascotEngineAdapter`` / ``TutorDecisionEngine`` 互相独立：引擎路径仍可
  走决策管线；当 ``MASCOT_USE_MINIMAX_DIRECT=1`` 时由本模块直接驱动 LLM。
- 当 MiniMax API Key 未配置时直接抛出 ``RuntimeError``，由调用方降级处理。
"""

from __future__ import annotations

import logging
import os
import re
from typing import AsyncGenerator, Iterable

from config import settings
from llm_stream import call_llm_stream_messages

logger = logging.getLogger("starlearn.mascot.llm")

# 小星角色默认温度（与 mascot.MascotChatRequest 默认值保持一致）。
MASCOT_DEFAULT_TEMPERATURE: float = 0.8

# 多轮对话保留的最大消息条数（与前端 js/mascot-services.js slice(-20) 对齐）。
MAX_HISTORY_MESSAGES: int = 20

# 注入到 system prompt 的占位符集合 —— 与 MASCOT_SYSTEM_PROMPT 中的
# {page_context} / {user_profile} / {today_stats} 三处对应。
_PLACEHOLDER_RE = re.compile(r"\{(page_context|user_profile|today_stats)\}")


# ---------------------------------------------------------------------------
# 上下文注入辅助
# ---------------------------------------------------------------------------


def _truncate(value: str, limit: int = 800) -> str:
    """防止超长字段撑爆 prompt；超过 limit 字时截断并加省略号。"""
    if not value:
        return ""
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def render_mascot_system_prompt(
    system_prompt_template: str,
    *,
    page_context: str = "",
    user_profile: str = "",
    today_stats: str = "",
) -> str:
    """把 ``MASCOT_SYSTEM_PROMPT`` 模板中的占位符替换成真实上下文。"""
    return _PLACEHOLDER_RE.sub(
        lambda m: {
            "page_context": _truncate(page_context) or "（未提供页面上下文）",
            "user_profile": _truncate(user_profile, 1200) or "（暂无用户画像）",
            "today_stats": _truncate(today_stats) or "（暂无今日学习数据）",
        }[m.group(1)],
        system_prompt_template,
    )


def build_mascot_messages(
    *,
    system_prompt: str,
    user_message: str,
    conversation_history: Iterable[dict] | None = None,
) -> list[dict[str, str]]:
    """拼装 MiniMax Chat Completions 所需的 messages 数组。

    ``conversation_history`` 元素形如 ``{"role": "user"|"assistant", "content": "..."}``，
    非法条目会被静默丢弃。
    """
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        history_list = list(conversation_history)[-MAX_HISTORY_MESSAGES:]
        for item in history_list:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role not in ("user", "assistant", "system"):
                continue
            if not isinstance(content, str) or not content.strip():
                continue
            # 历史中的 system 消息与最新 system prompt 冲突时丢弃，避免覆盖。
            if role == "system":
                continue
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message})
    return messages


def resolve_minimax_model(requested: str | None) -> str:
    """解析最终要调用的模型名。

    - 当 ``requested`` 为空、为字面 ``"default"`` 或与历史默认 ``MiniMax-Text-01`` 相同时，
      统一回退到 ``settings.minimax_model_name``，避免请求方误传其它平台模型。
    - 其它情况信任请求方传入的字符串。
    """
    fallback = settings.minimax_model_name or "MiniMax-Text-01"
    if not requested:
        return fallback
    normalized = requested.strip()
    if not normalized or normalized.lower() in {"default", "minimax-text-01"}:
        return fallback
    return normalized


# ---------------------------------------------------------------------------
# 主服务
# ---------------------------------------------------------------------------


class MascotLLMService:
    """小星 → MiniMax 大模型 API 接入服务。

    使用方式::

        service = MascotLLMService()
        async for chunk in service.stream_chat(
            user_message="怎么理解 Python 装饰器？",
            system_prompt=MASCOT_SYSTEM_PROMPT,
            page_context="课程学习页 - Python 基础",
            conversation_history=[],
        ):
            ...

    任何对 ``llm_stream`` 的调用都已经在项目级配置中默认指向 MiniMax
    (``settings.minimax_api_url`` + ``settings.minimax_api_key``)，
    故本服务不需要额外的 provider 切换逻辑。
    """

    # 当 ``MASCOT_FALLBACK_NO_LLM=1`` 时直接抛出，避免真实 LLM 调用 —— 用于测试。
    _SKIP_LLM_ENV = "MASCOT_FALLBACK_NO_LLM"

    def __init__(self) -> None:
        self._skip_llm = os.environ.get(self._SKIP_LLM_ENV) == "1"

    # -- 健康检查 ----------------------------------------------------------

    def is_available(self) -> bool:
        """MiniMax API Key 是否已配置 —— 供前端 /api/mascot/config 使用。"""
        return bool(settings.minimax_api_key)

    # -- 对外主入口 --------------------------------------------------------

    async def stream_chat(
        self,
        *,
        user_message: str,
        system_prompt: str,
        page_context: str = "",
        user_profile: str = "",
        today_stats: str = "",
        conversation_history: Iterable[dict] | None = None,
        model: str | None = None,
        temperature: float = MASCOT_DEFAULT_TEMPERATURE,
    ) -> AsyncGenerator[str, None]:
        """流式调用 MiniMax 大模型，逐 chunk yield 文本片段。

        当 ``MASCOT_FALLBACK_NO_LLM=1`` 时不发起网络请求，直接 yield 一段固定
        文本，方便单测。
        """
        if not user_message or not user_message.strip():
            raise ValueError("user_message is required")

        if self._skip_llm:
            yield "[小星-MiniMax fallback] 已跳过真实 LLM 调用 (MASCOT_FALLBACK_NO_LLM=1)"
            return

        if not self.is_available():
            raise RuntimeError("MiniMax API Key 未配置 (minimax_api_key)")

        rendered_system = render_mascot_system_prompt(
            system_prompt,
            page_context=page_context,
            user_profile=user_profile,
            today_stats=today_stats,
        )
        messages = build_mascot_messages(
            system_prompt=rendered_system,
            user_message=user_message,
            conversation_history=conversation_history,
        )

        target_model = resolve_minimax_model(model)
        logger.info(
            "[MascotLLMService] → MiniMax model=%s temp=%.2f msgs=%d",
            target_model,
            temperature,
            len(messages),
        )

        async for chunk in call_llm_stream_messages(
            messages=messages,
            temperature=temperature,
            model=target_model,
        ):
            if chunk:
                yield chunk
