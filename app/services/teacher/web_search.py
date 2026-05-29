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

# B站 API 基础 URL（用于验证视频有效性）
BILIBILI_API_URL = "https://api.bilibili.com/x/web-interface/view"


# 用于 B站 API 请求的标准浏览器请求头（避免被反爬虫拦截）
_BILI_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


async def _verify_bilibili_video(bvid: str) -> bool:
    """
    通过 B站 API 验证视频是否有效。

    Args:
        bvid: B站视频 BV 号，如 "BV1xx411c7mD"

    Returns:
        True 如果视频存在且有效，False 如果视频已删除/下架/不存在/请求被拦截
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                BILIBILI_API_URL,
                params={"bvid": bvid},
                headers=_BILI_HEADERS,
            )
            if response.status_code != 200:
                logger.warning("B站 API 返回 HTTP %d: %s", response.status_code, bvid)
                return False
            data = response.json()
            code = data.get("code")
            if code == 0:
                # 额外检查：视频是否被下架（state 字段）
                video_data = data.get("data", {})
                state = video_data.get("state", 0)
                # state == 0 表示正常，其他值可能表示各种问题
                if state == 0:
                    return True
                logger.info("B站视频 %s state=%d，可能已失效", bvid, state)
                return False
            # -404 表示视频不存在，-412 表示请求被拦截
            logger.info("B站视频 %s 验证失败: code=%s, message=%s", bvid, code, data.get("message", ""))
            return False
    except Exception as e:
        logger.warning("B站视频验证异常 %s: %s", bvid, e)
        return False


def _extract_bvid(url: str) -> str | None:
    """从 B站 URL 中提取 BV 号，支持多种格式"""
    import re
    patterns = [
        # 标准视频页
        r"bilibili\.com/video/(BV\w+)",
        # 带查询参数的视频页
        r"bilibili\.com/video/(BV\w+)(?:\?|/|$)",
        # 短链接
        r"b23\.tv/(BV\w+)",
        # m.bilibili.com 移动端
        r"m\.bilibili\.com/video/(BV\w+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _is_bilibili_video_url(url: str) -> bool:
    """判断 URL 是否为 B站视频页面（而非搜索页/用户空间/专栏等）"""
    import re
    # 只保留真正的视频页面链接
    video_patterns = [
        r"bilibili\.com/video/(BV\w+|av\d+)",
        r"b23\.tv/\w+",
        r"m\.bilibili\.com/video/(BV\w+|av\d+)",
    ]
    for pattern in video_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


async def filter_valid_bilibili_links(results: list[SearchResult]) -> list[SearchResult]:
    """
    过滤搜索结果：
    1. 移除非 B站视频页面（如搜索结果页、用户空间、专栏等）
    2. 对已失效的 B站视频链接调用 API 验证并过滤
    3. 非 B站链接直接保留
    """
    if not results:
        return []

    valid_results = []
    bili_links_to_check = []

    for result in results:
        if not _is_bilibili_video_url(result.url):
            # 非 B站视频页面（可能是搜索结果页、用户主页、专栏等）
            # 如果包含 bilibili.com 但不是视频页，直接过滤掉
            if "bilibili.com" in result.url.lower() or "b23.tv" in result.url.lower():
                logger.info("过滤非 B站视频页面: %s (%s)", result.url[:60], result.title[:40])
                continue
            # 其他非 B站链接保留
            valid_results.append(result)
            continue

        # 是 B站视频页面，需要验证
        bvid = _extract_bvid(result.url)
        if bvid:
            bili_links_to_check.append((result, bvid))
        else:
            # 是视频页面但提取不到 BV 号（可能是 av 号），保留待后续处理
            valid_results.append(result)

    # 串行验证 B站链接（避免触发限流）
    for result, bvid in bili_links_to_check:
        is_valid = await _verify_bilibili_video(bvid)
        if is_valid:
            valid_results.append(result)
            logger.info("B站视频验证通过: %s (%s)", bvid, result.title[:40])
        else:
            logger.warning("B站视频已失效，过滤掉: %s (%s)", bvid, result.title[:40])

    # 保持原始顺序
    url_order = {r.url: i for i, r in enumerate(results)}
    valid_results.sort(key=lambda r: url_order.get(r.url, 999))

    return valid_results


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


async def search_minimax(query: str) -> SearchResponse | None:
    """
    调用 MiniMax Coding Plan MCP web_search 工具（通过 Function Calling）。

    优先使用 MiniMax 搜索，失败返回 None 由调用方处理（降级到 Tavily）。

    Args:
        query: 搜索关键词

    Returns:
        SearchResponse on success, None on failure/限速
    """
    from config import settings

    payload = {
        "model": settings.minimax_search_model,
        "messages": [
            {"role": "user", "content": f"搜索：{query}"}
        ],
        "tools": [{
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "搜索互联网获取最新信息。当需要补充背景知识或回答超出教材范围的问题时调用。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词或问题",
                        },
                    },
                    "required": ["query"],
                },
            },
        }],
        "tool_choice": {"type": "function", "function": {"name": "web_search"}},
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.minimax_api_key}",
        "GroupId": settings.minimax_group_id,
    }

    logger.info("MiniMax search: query=%s", query[:80])

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.minimax_search_api_url}/chat/completions",
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                logger.error(
                    "MiniMax search API error HTTP %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                return None

            data = response.json()

            # 解析 MiniMax 返回 —— 搜索结果在 message.content 中
            message = data.get("choices", [{}])[0].get("message", {})
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])

            # MiniMax 在 function calling 模式下，搜索结果通常在 content 中返回
            if content:
                logger.info("MiniMax search: got answer in content, len=%d, query=%s", len(content), query[:80])
                return SearchResponse(query=query, answer=content, results=[], source_count=0)

            if not tool_calls:
                # 没有触发 web_search 工具，返回 None 降级
                logger.warning("MiniMax search: no tool_calls triggered and no content, query=%s", query[:80])
                return None

            # 备用：解析 tool_call 结果（部分 MiniMax 版本可能在 tool_calls 中返回）
            results = []
            answer = ""
            for tc in tool_calls:
                func = tc.get("function", {})
                if func.get("name") == "web_search":
                    args_str = func.get("arguments", "{}")
                    try:
                        import json as _json
                        args = _json.loads(args_str)
                        logger.info("MiniMax web_search triggered with query: %s", args.get("query", ""))
                    except Exception:
                        pass

            # 如果 content 为空且 tool_calls 也无实质结果，返回 None 降级到 Tavily
            logger.warning("MiniMax search: no content in response, falling back to Tavily, query=%s", query[:80])
            return None

    except httpx.TimeoutException:
        logger.error("MiniMax search timeout for query: %s", query[:80])
        return None
    except Exception as e:
        logger.error("MiniMax search failed: %s", e)
        return None


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

    # 按相关性分数降序排序，过滤低分结果，只保留最相关的给 LLM
    filtered_results = [
        r for r in sorted(search_response.results, key=lambda x: x.score, reverse=True)
        if r.score >= 0.3  # Tavily 分数阈值过滤
    ][:5]  # 最多给 LLM 看 5 条

    for i, result in enumerate(filtered_results, 1):
        entry = f"### 来源 {i}: {result.title}\n"
        entry += f"URL: {result.url}\n"
        content = result.content[:500]  # 每篇最多 500 字
        entry += f"内容: {content}\n"

        if total_chars + len(entry) > max_chars:
            parts.append(f"\n*(共 {len(filtered_results)} 条结果，已截断到 {i-1} 条)*")
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
