# -*- coding: utf-8 -*-
"""
Tavily 网页搜索工具

对应 OpenMAIC lib/web-search/tavily.ts + app/api/web-search/route.ts

用法:
    from app.services.teacher.web_search import search_web, format_as_context

    results = await search_web("Python 列表推导式", api_key="tvly-...")
    context = format_as_context(results)  # → 注入 LLM 上下文
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger("starlearn.web_search")

# 默认 API Key（可通过环境变量 TAVILY_API_KEY 覆盖）
import os
DEFAULT_API_KEY = os.getenv("TAVILY_API_KEY", "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")

TAVILY_API_URL = "https://api.tavily.com/search"


@dataclass
class SearchResult:
    """单条搜索结果"""
    title: str
    url: str
    content: str
    score: float = 0.0


@dataclass
class SearchResponse:
    """搜索响应"""
    query: str
    answer: str = ""           # Tavily 生成的 AI 摘要
    results: list[SearchResult] = field(default_factory=list)
    response_time: float = 0.0
    source_count: int = 0


async def search_web(
    query: str,
    api_key: str = "",
    search_depth: str = "basic",
    max_results: int = 5,
    include_answer: bool = True,
) -> SearchResponse:
    """
    调用 Tavily Search API。

    Args:
        query: 搜索关键词
        api_key: Tavily API key（默认使用内置 key）
        search_depth: "basic" | "advanced"
        max_results: 返回结果数 (1-20)
        include_answer: 是否包含 AI 摘要

    Returns:
        SearchResponse with results and optional AI answer
    """
    key = api_key or DEFAULT_API_KEY
    if not key:
        raise RuntimeError("Tavily API key not configured")

    payload = {
        "api_key": key,
        "query": query.strip(),
        "search_depth": search_depth,
        "max_results": max_results,
        "include_answer": include_answer,
        "include_raw_content": False,
    }

    logger.info("Tavily search: query=%s, depth=%s", query[:80], search_depth)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(TAVILY_API_URL, json=payload)
            if response.status_code != 200:
                logger.error("Tavily API error HTTP %d: %s", response.status_code, response.text[:200])
                return SearchResponse(query=query, source_count=0)

            data = response.json()

            results = [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    content=r.get("content", ""),
                    score=r.get("score", 0.0),
                )
                for r in data.get("results", [])
            ]

            resp = SearchResponse(
                query=data.get("query", query),
                answer=data.get("answer", ""),
                results=results,
                response_time=data.get("response_time", 0.0),
                source_count=len(results),
            )

            logger.info(
                "Tavily search complete: query=%s, results=%d, answer_len=%d, time=%.2fs",
                resp.query, resp.source_count, len(resp.answer), resp.response_time,
            )
            return resp

    except httpx.TimeoutException:
        logger.error("Tavily search timeout for query: %s", query[:80])
        return SearchResponse(query=query, source_count=0)
    except Exception as e:
        logger.error("Tavily search failed: %s", e)
        return SearchResponse(query=query, source_count=0)


def format_as_context(search_response: SearchResponse, max_chars: int = 3000) -> str:
    """
    将搜索结果格式化为 LLM 可用的上下文字符串。

    对应 OpenMAIC lib/web-search/tavily.ts 的 formatSearchResultsAsContext()

    格式:
        ## 网络搜索结果
        **AI 摘要**: ...

        ### 来源 1: 标题
        URL: ...
        内容: ...

        ### 来源 2: ...
    """
    parts = ["## 网络搜索结果\n"]

    if search_response.answer:
        parts.append(f"**AI 摘要**: {search_response.answer}\n")

    total_chars = sum(len(p) for p in parts)

    for i, result in enumerate(search_response.results, 1):
        entry = f"### 来源 {i}: {result.title}\n"
        entry += f"URL: {result.url}\n"
        content = result.content[:500]  # 每篇最多 500 字
        entry += f"内容: {content}\n"

        if total_chars + len(entry) > max_chars:
            parts.append(f"\n*(共 {search_response.source_count} 条结果，已截断到 {i-1} 条)*")
            break

        parts.append(entry)
        total_chars += len(entry)

    return "\n".join(parts)


def format_as_speech_context(search_response: SearchResponse) -> str:
    """
    将搜索结果格式化为适合教师语音输出的简短摘要。
    用于 LLM 将搜索结果整合为口语化讲解。
    """
    if not search_response.results and not search_response.answer:
        return "未能找到相关信息。"

    lines = []
    if search_response.answer:
        lines.append(f"摘要：{search_response.answer[:300]}")

    if search_response.results:
        lines.append(f"\n找到 {search_response.source_count} 条相关来源：")
        for i, r in enumerate(search_response.results[:3], 1):
            lines.append(f"{i}. {r.title}: {r.content[:150]}...")

    return "\n".join(lines)


# =============================================================================
# Function Calling Tool 定义
# =============================================================================

WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "搜索互联网获取最新信息。当学生提问超出当前课堂上下文、"
            "需要补充背景知识、验证事实或获取最新动态时调用此工具。"
            "搜索结果将被整合为口语化的连贯回复。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词。使用中文，简洁明确。例如'Python列表推导式语法'而非'Python里怎么用那个方括号的写法'",
                },
            },
            "required": ["query"],
        },
    },
}
