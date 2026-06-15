# -*- coding: utf-8 -*-
"""Phase 2 — 通用 LLM JSON 解析器(替换 libs/course.py:_extract_json 的脆弱正则).

职责:
  1. build_prompt(prompt_id, **vars) → system_prompt
  2. call_llm_async(system_prompt, user_prompt) → raw text
  3. 抽 JSON 块(处理 ```json``` 围栏 + 前言垃圾)
  4. Pydantic 校验,失败自动 retry 1 次(retry 时追加 "上次输出不符合 schema, 错误: <msg>, 严格按 schema 重出")
  5. 仍失败 → 抛 LLMJsonError,上层 catch 后写 fallback
"""
from __future__ import annotations

import json
import logging
import re
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from llm_stream import call_llm_async
from prompts import build_prompt

logger = logging.getLogger("starlearn.llm_json")

T = TypeVar("T", bound=BaseModel)


class LLMJsonError(Exception):
    """LLM 输出经 2 次尝试后仍不符合 schema."""


# ============================================================
# 内部工具
# ============================================================

_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*([\s\S]+?)```", re.MULTILINE)
# 截断检测: 末尾 100 字符中含 ``` 但没有闭合的 fence
_TRUNCATED_RE = re.compile(r"```\s*\{[^}]*$", re.MULTILINE)
# 简易 JSON 平衡检测(粗略,但能 catch 截断)
_OPEN_BRACES_RE = re.compile(r"[\{\[]")
_CLOSE_BRACES_RE = re.compile(r"[\}\]]")


def _strip_think(text: str) -> str:
    """剥掉 <think>...</think> 这种推理痕迹(MiniMax 习惯)."""
    return re.sub(r"<think>[\s\S]*?</think>", "", text)


def _extract_json_block(text: str) -> str:
    """从 LLM 输出里抠出最大可能的 JSON 块.

    策略:
      1. 剥 <think>
      2. 找 ```json ... ``` 围栏,取第一个
      3. 没围栏就找最外层 { ... } / [ ... ] 配对
    """
    text = _strip_think(text).strip()

    # 围栏
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()

    # 找第一个 { 或 [
    first_open = -1
    for i, ch in enumerate(text):
        if ch in "{[":
            first_open = i
            break
    if first_open < 0:
        return text  # 调用方再 json.loads 兜底

    # 反向配对
    open_ch = text[first_open]
    close_ch = "}" if open_ch == "{" else "]"
    depth = 0
    in_str = False
    escape = False
    for j in range(first_open, len(text)):
        ch = text[j]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[first_open:j + 1]

    # 找不到配对 — 视为截断
    raise LLMJsonError("LLM 输出 JSON 未闭合,疑似截断")


def _try_parse_obj(raw: str) -> dict | list:
    """宽松 json.loads,失败抛 ValueError."""
    return json.loads(raw)


# ============================================================
# 公开 API
# ============================================================

async def llm_json(
    prompt_id: str,
    variables: dict,
    schema: Type[T],
    *,
    temperature: float = 0.3,
    max_retries: int = 1,
) -> T:
    """调 LLM, 抽 JSON, Pydantic 校验;失败自动 retry,仍失败抛 LLMJsonError.

    Args:
        prompt_id: prompts.PROMPT_TEMPLATES 里的 key
        variables: build_prompt 用的模板变量
        schema: 目标 Pydantic 模型类
        temperature: LLM temperature
        max_retries: 校验失败后追加 retry 次数(默认 1)

    Returns:
        schema 的实例

    Raises:
        LLMJsonError: 经 max_retries+1 次尝试后仍失败
    """
    system_prompt = build_prompt(prompt_id, **variables)
    last_error: str = ""

    for attempt in range(max_retries + 1):
        user_prompt = _build_user_prompt(variables, attempt, last_error)
        try:
            raw = await call_llm_async(system_prompt, user_prompt, temperature=temperature)
        except Exception as e:
            last_error = f"LLM 调用失败: {e}"
            logger.warning(f"[llm_json] {prompt_id} attempt {attempt} 调用失败: {e}")
            continue

        try:
            block = _extract_json_block(raw)
            obj = _try_parse_obj(block)
            instance = schema.model_validate(obj)
            return instance
        except (ValueError, ValidationError, LLMJsonError) as e:
            last_error = f"{type(e).__name__}: {e}"
            logger.warning(
                f"[llm_json] {prompt_id} attempt {attempt} 解析失败: {last_error}; raw[:200]={raw[:200]!r}"
            )
            continue

    raise LLMJsonError(
        f"prompt_id={prompt_id} 经 {max_retries + 1} 次尝试仍无法得到符合 schema 的输出. 最后错误: {last_error}"
    )


def _build_user_prompt(variables: dict, attempt: int, last_error: str) -> str:
    """根据 attempt 决定是否追加"上次错了,严格按 schema 重出"提示."""
    if attempt == 0:
        return _variables_to_user(variables)

    return (
        _variables_to_user(variables)
        + "\n\n---\n⚠️ 你上一次的输出未能通过校验: "
        + last_error[:300]
        + "\n请严格按上方 schema 输出 JSON,不要再加任何额外文字或围栏。"
    )


def _variables_to_user(variables: dict) -> str:
    """把 variables 序列化成 user_prompt 文本."""
    parts: list[str] = []
    for k, v in variables.items():
        if isinstance(v, (dict, list)):
            parts.append(f"## {k}\n```json\n{json.dumps(v, ensure_ascii=False, indent=2)}\n```")
        else:
            parts.append(f"## {k}\n{v}")
    return "\n\n".join(parts)


# ============================================================
# 调试钩子(单元测试用)
# ============================================================

def _reset_extract_for_test() -> None:
    """测试时清空缓存状态(目前没有状态,占位)."""
    return None
