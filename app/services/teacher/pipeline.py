# -*- coding: utf-8 -*-
"""
AI 教师对话 Pipeline — 工具集成中枢

将 draw_svg、web_search、grade_quiz 等工具注册到 SSE 流式对话管道中。

工作流程:
  1. 用户输入 → LLM 流式生成（带 UI Action JSON + Function Calling）
  2. LLM 输出中的 function_call → ToolExecutor 执行 → 结果注入上下文
  3. LLM 输出中的 UI action (speech/spotlight/wb_draw_svg/...) → SSE push 到前端
  4. 前端 SyncEngine 消费 SSE 流 → TTS 播放 + 白板绘制 + 字级高亮

工具分工:
  - UI Action (JSON 数组): speech, spotlight, laser, wb_draw_svg, wb_draw_text, ...
  - Function Calling (tools 参数): web_search, grade_quiz, search_knowledge_base, run_code
"""

from __future__ import annotations

import json
import logging
import re
from typing import AsyncIterator

from app.services.teacher.tool_executor import ToolExecutor
from app.services.teacher.personas import get_persona_manager
from app.services.teacher.function_tools import BACKEND_TOOLS
from app.services.teacher.web_search import format_as_speech_context

logger = logging.getLogger("starlearn.pipeline")


# 自动触发搜索的关键词（不区分大小写）
_AUTO_SEARCH_KEYWORDS = [
    "推荐", "视频", "教程", "链接", "资源", "课程", "网站", "网址",
    "b站", "bilibili", "哔哩哔哩", "youtube", "油管",
    "哪里看", "哪里学", "有什么好的", "求推荐", "有没有",
    "文档", "官方", "github", "博客", "文章",
]

# 搜索 query 停用词（需要过滤掉的无关词）
_SEARCH_STOP_WORDS = [
    # 人称/请求
    "给我", "帮我", "帮我找", "为我", "替我",
    # 推荐相关
    "推荐", "推荐一下", "推荐几个", "推荐一些",
    # 数量/程度
    "一些", "几个", "一点", "有些", "好些", "好些个",
    "好的", "优质的", "不错的", "很好的", "很好的", "棒的", "厉害的",
    "经典", "著名", "知名", "热门", "流行",
    # 情态/疑问
    "可以", "吗", "请问", "你知道", "你知道的",
    "有没有", "有木有", "哪里有", "在哪", "在哪找",
    "想", "想要", "要", "需要", "还得", "还要",
    # 动作辅助
    "帮忙", "帮", "找", "找一下", "找几个", "搜", "搜一下",
    "一下", "一下下",
    # 语气词
    "呢", "吧", "啊", "哦", "嗯", "哈", "呗", "啦", "咯", "嘛",
    # 称呼
    "大家", "各位", "亲们", "大佬", "大神", "高手", "前辈", "老师",
    # 感谢/急切
    "拜托", "谢谢", "感谢", "求", "跪求", "急", "急需", "急求",
    # 位置/方向
    "上", "里面", "中", "里面", "里边",
    # 通用填充词
    "那个", "这个", "那种", "这种",
]

# 站点限定映射（当用户提到特定平台时，加入 site: 限定提升相关性）
_SITE_HINTS = {
    "b站": "bilibili.com",
    "bilibili": "bilibili.com",
    "哔哩哔哩": "bilibili.com",
    "youtube": "youtube.com",
    "油管": "youtube.com",
    "github": "github.com",
    "git": "github.com",
    "知乎": "zhihu.com",
    "csdn": "csdn.net",
    "掘金": "juejin.cn",
    "简书": "jianshu.com",
    "豆瓣": "douban.com",
    "百度": "baidu.com",
    "博客园": "cnblogs.com",
}


def _refine_search_query(user_input: str) -> str:
    """
    将用户的自然语言输入提炼为精确的搜索关键词。
    去除礼貌用语、语气词、冗余词，保留核心实体。
    当检测到特定站点时，自动加入 site: 限定。
    """
    original = user_input.strip()
    query = original.lower()

    # 1. 去除停用词（按长度降序，先匹配长的）
    for word in sorted(_SEARCH_STOP_WORDS, key=len, reverse=True):
        query = query.replace(word, " ")

    # 2. 去除多余空格
    query = " ".join(query.split())

    # 3. 如果提炼后太短（<5字），回退到原始输入的核心部分
    if len(query) < 5:
        # 尝试提取引号内的内容
        quoted = re.findall(r'["""](.+?)["""]', original)
        if quoted:
            query = quoted[0]
        else:
            query = original.strip()

    # 4. 去除末尾标点
    query = query.strip("　、，。！？.;:").strip()

    # 5. 检测站点限定
    site_qualifier = ""
    for hint, domain in _SITE_HINTS.items():
        if hint in original.lower():
            site_qualifier = f" site:{domain}"
            break

    # 6. 组合最终 query
    final_query = query + site_qualifier
    return final_query.strip()


class TeacherPipeline:
    """
    AI 教师对话管道。

    用法:
        pipeline = TeacherPipeline()
        async for event in pipeline.run(
            user_input="什么是HDFS?",
            persona="expert_mentor",
            student_id="u_123",
        ):
            yield event  # SSE 事件
    """

    def __init__(self):
        self.tool_executor = ToolExecutor()

    @staticmethod
    def _should_auto_search(user_input: str) -> bool:
        """检测用户输入是否需要自动触发搜索（资源推荐类问题）。"""
        text = user_input.lower()
        return any(kw in text for kw in _AUTO_SEARCH_KEYWORDS)

    async def run(
        self,
        user_input: str,
        persona: str = "expert_mentor",
        student_id: str = "",
        course_id: str = "",
        scene_context: dict | None = None,
        student_profile: dict | None = None,
    ) -> AsyncIterator[dict]:
        """
        运行完整的 AI 教师对话管道。

        Yields:
            {"event": "asr_result", "data": {...}}
            {"event": "action", "data": {...}}
            {"event": "function_call", "data": {"name": "web_search", "arguments": {...}}}
            {"event": "function_result", "data": {...}}
            {"event": "done", "data": {...}}
        """
        # 1. 组装 System Prompt
        mgr = get_persona_manager()
        system_prompt = mgr.build_system_prompt(
            persona_id=persona,
            student_profile=student_profile,
            scene_context=scene_context,
        )

        # 1b. 检索相关记忆
        retrieved_memories, retrieval_logs = [], []
        if student_id:
            try:
                from app.services.memory_retriever import retrieve_memories_with_logs, format_memories_for_prompt
                retrieved_memories, retrieval_logs = retrieve_memories_with_logs(
                    user_id=student_id,
                    current_input=user_input,
                    limit=6,
                    min_confidence=0.5,
                )
            except Exception as e:
                logger.warning(f"[Pipeline] 记忆检索失败: {e}")

        # 注入记忆到 system prompt
        memory_prompt = format_memories_for_prompt(retrieved_memories)
        if memory_prompt:
            system_prompt += "\n" + memory_prompt

        # 发送记忆检索日志到前端（thinking链路）
        if retrieval_logs:
            yield {
                "event": "memory_retrieval_logs",
                "data": {
                    "logs": retrieval_logs,
                    "count": len(retrieval_logs),
                },
            }

        # 1c. 自动搜索（关键词触发，不依赖 LLM 判断）
        auto_search_context = ""
        if self._should_auto_search(user_input):
            try:
                refined_query = _refine_search_query(user_input)
                logger.info("[Pipeline] 自动触发搜索: 原始='%s' 优化='%s'", user_input[:60], refined_query[:60])
                search_result = await self.tool_executor.execute_function_call(
                    "web_search", {"query": refined_query}
                )
                auto_search_context = search_result.get("context_for_llm", "")
                if auto_search_context:
                    logger.info("[Pipeline] 自动搜索完成，结果长度: %d", len(auto_search_context))
                    yield {
                        "event": "function_result",
                        "data": {
                            "name": "web_search",
                            "result": search_result,
                            "auto_triggered": True,
                        },
                    }
            except Exception as e:
                logger.warning("[Pipeline] 自动搜索失败: %s", e)

        # 2. 构建消息（带 Function Calling tools）
        user_prompt_parts = [
            f"学生说：{user_input}\n\n",
            "请按照你的教学风格，用碎片化交织的方式回复。",
            "边说边画，边说边指。\n\n",
        ]

        if auto_search_context:
            # 已自动搜索过，把结果喂给 LLM，要求直接输出 <links>
            user_prompt_parts.extend([
                "【系统已自动搜索到以下真实信息，请基于这些信息回复】\n",
                auto_search_context,
                "\n\n要求：\n",
                "1. 用碎片化交织的方式输出教学内容\n",
                "2. 在 JSON 数组之后用 <links>[...]</links> 标记输出上面搜索结果中的真实链接\n",
                "3. <links> 中的 URL 必须来自上面的搜索结果，严禁编造\n",
                "4. 每个链接包含：type(external)、title、url、description、icon\n",
                "5. 严禁使用 Markdown 链接格式 [标题](URL)\n",
            ])
        else:
            user_prompt_parts.extend([
                "如果学生的问题涉及外部资源推荐（如视频、教程、文档），"
                "你必须先调用 web_search 工具搜索真实链接，"
                "然后在回复末尾用 <links> 标记输出这些真实可点击的链接。"
                "严禁编造 URL。\n\n"
                "调用搜索的方式：在 JSON 数组之前输出 "
                "`<function_call>{\"name\": \"web_search\", \"arguments\": {\"query\": \"搜索关键词\"}}</function_call>`\n"
                "例如：`<function_call>{\"name\": \"web_search\", \"arguments\": {\"query\": \"Python 冒泡排序 B站 视频\"}}</function_call>`"
            ])

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "".join(user_prompt_parts)},
        ]

        # 3. LLM 流式生成
        full_response = ""
        function_calls = []

        async for chunk in self._stream_llm_with_tools(messages, BACKEND_TOOLS):
            if chunk["type"] == "text":
                full_response += chunk["content"]
                yield {"event": "text_delta", "data": {"content": chunk["content"]}}

            elif chunk["type"] == "function_call":
                # LLM 决定调用工具
                fc = {
                    "id": chunk.get("id", ""),
                    "name": chunk["name"],
                    "arguments": chunk["arguments"],
                }
                function_calls.append(fc)
                yield {"event": "function_call", "data": fc}

        # 4. 执行 Function Calling 工具
        function_results = []
        for fc in function_calls:
            try:
                result = await self.tool_executor.execute_function_call(
                    fc["name"], fc["arguments"]
                )
                function_results.append({
                    "name": fc["name"],
                    "result": result,
                })
                yield {"event": "function_result", "data": {
                    "name": fc["name"],
                    "result": result,
                }}
            except Exception as e:
                logger.error("Function call '%s' failed: %s", fc["name"], e)
                yield {"event": "function_result", "data": {
                    "name": fc["name"],
                    "error": str(e),
                }}

        # 5. 如果触发了工具，进行第二轮 LLM 调用（整合结果）
        if function_results:
            context_parts = []
            for fr in function_results:
                if fr["name"] == "web_search":
                    context_parts.append(fr["result"].get("context_for_llm", ""))
                elif fr["name"] == "search_knowledge_base":
                    kb_results = fr["result"].get("results", [])
                    if kb_results:
                        context_parts.append("本地知识库检索结果:\n" + json.dumps(kb_results, ensure_ascii=False))

            if context_parts:
                context_text = "\n\n".join(context_parts)
                # 如果第一轮有文本输出，保留；否则用占位符表示工具调用
                assistant_content = full_response[:500] if full_response.strip() else "（已调用搜索工具获取最新信息）"
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": (
                    f"以下是从网络/知识库搜索到的真实信息，请基于这些信息回复学生：\n\n{context_text}\n\n"
                    "要求：\n"
                    "1. 用碎片化交织的方式输出教学内容\n"
                    "2. 如果搜索结果中有相关网页链接，在 JSON 数组之后用 <links>[...]</links> 标记输出这些真实链接\n"
                    "3. <links> 中的 URL 必须来自上面的搜索结果，严禁编造\n"
                    "4. 每个链接包含：type(internal/external)、title、url、description、icon"
                )})

                full_response = ""
                async for chunk in self._stream_llm_with_tools(messages, None):
                    if chunk["type"] == "text":
                        full_response += chunk["content"]
                        yield {"event": "text_delta", "data": {"content": chunk["content"]}}

        # 6. 解析 UI Action JSON 数组
        actions = self._extract_actions(full_response)
        if actions:
            for action in actions:
                # 预处理：为 speech 预生成 TTS
                if action.get("type") == "speech":
                    action = await self.tool_executor.preprocess_ui_action(action)
                yield {"event": "action", "data": action}

        # 7. 提取学习链接推荐
        links = self._extract_links(full_response)

        # 清理输出中的 links 标记，避免前端显示原始 JSON
        full_response = re.sub(r'<links>[\s\S]*?</links>', '', full_response).strip()

        # 8. 完成
        done_data = {
            "agent": "teacher",
            "persona": persona,
            "full_text": full_response,
            "action_count": len(actions) if actions else 0,
            "function_calls": len(function_calls),
            "memory_refs": [
                {"id": m.get("id"), "content": m.get("content", ""), "type": m.get("memory_type", "fact")}
                for m in retrieved_memories[:3]
            ] if retrieved_memories else [],
        }
        if links:
            done_data["links"] = links
        yield {"event": "done", "data": done_data}

    # ---- LLM 流式调用 ----

    async def _stream_llm_with_tools(
        self, messages: list[dict], tools: list[dict] | None
    ) -> AsyncIterator[dict]:
        """
        调用 LLM 流式生成（带 Function Calling tools）。

        策略：
        - 若传了 tools，直接调用 MiniMax API 并解析结构化响应（tool_calls）。
        - 若未传 tools，使用 call_llm_async 获取纯文本后逐字符模拟流式输出。
        """
        try:
            if tools:
                from llm_stream import get_http_client
                from config import settings

                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.minimax_api_key}",
                }
                payload = {
                    "model": settings.minimax_model_name,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 8192,
                    "tools": tools,
                }

                client = await get_http_client()
                response = await client.post(
                    f"{settings.minimax_api_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

                if response.status_code != 200:
                    snippet = response.text[:800]
                    logger.error("MiniMax API error HTTP %d: %s", response.status_code, snippet)
                    yield {"type": "text", "content": f"[系统错误: MiniMax 返回 HTTP {response.status_code}]"}
                    return

                body = response.json()
                message = body["choices"][0]["message"]
                content = message.get("content") or ""
                tool_calls = message.get("tool_calls", [])

                # 优先处理标准 tool_calls
                if tool_calls:
                    for tc in tool_calls:
                        func = tc.get("function", {})
                        try:
                            args = json.loads(func.get("arguments", "{}"))
                        except json.JSONDecodeError:
                            args = {}
                        yield {
                            "type": "function_call",
                            "id": tc.get("id", "fc_1"),
                            "name": func.get("name", ""),
                            "arguments": args,
                        }
                    return

                # Fallback：检测文本中的 <function_call> 标记（MiniMax 可能以文本形式输出）
                fc_data = self._detect_function_call(content)
                if fc_data:
                    # 先输出 function_call 之前的文本
                    fc_match = re.search(r'<function_call>.*?</function_call>', content, re.DOTALL)
                    if fc_match:
                        before_text = content[:fc_match.start()]
                        for char in before_text:
                            yield {"type": "text", "content": char}
                    yield {
                        "type": "function_call",
                        "id": fc_data.get("id", "fc_1"),
                        "name": fc_data["name"],
                        "arguments": fc_data.get("arguments", {}),
                    }
                    # 输出 function_call 之后的文本
                    if fc_match:
                        after_text = content[fc_match.end():]
                        for char in after_text:
                            yield {"type": "text", "content": char}
                else:
                    for char in content:
                        yield {"type": "text", "content": char}
            else:
                from llm_stream import call_llm_async

                full_text = await call_llm_async(
                    messages[0]["content"],
                    messages[-1]["content"],
                    temperature=0.7,
                )

                for char in full_text:
                    yield {"type": "text", "content": char}

        except Exception as e:
            logger.error("LLM stream error: %s", e)
            yield {"type": "text", "content": f"[教师暂时无法回复: {e}]"}

    def _detect_function_call(self, text: str) -> dict | None:
        """
        从 LLM 输出中检测 function_call。

        支持格式:
          <function_call>{"name": "web_search", "arguments": {"query": "..."}}</function_call>
          或直接的 JSON function_call 对象
        """
        import re

        # 格式1: XML 标签包裹
        match = re.search(r'<function_call>(.*?)</function_call>', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 格式2: 直接的 function_call JSON 对象
        match = re.search(r'\{[^{}]*"name"\s*:\s*"(web_search|search_knowledge_base|grade_quiz|run_code|generate_course_outline)"[^{}]*\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if "name" in data:
                    return data
            except json.JSONDecodeError:
                pass

        return None

    @staticmethod
    def _extract_actions(raw_response: str) -> list[dict] | None:
        """从 LLM 原始输出中提取 JSON Action 数组"""
        import re
        text = raw_response.strip()

        if text.startswith("```"):
            text = re.sub(r"^```\w*\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        # 移除可能的 function_call 标签和 links 标记
        text = re.sub(r'<function_call>.*?</function_call>', '', text, flags=re.DOTALL)
        text = re.sub(r'<links>.*?</links>', '', text, flags=re.DOTALL)

        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return None

        try:
            actions = json.loads(match.group(0))
            if isinstance(actions, list):
                return actions
        except json.JSONDecodeError:
            pass
        return None

    @staticmethod
    def _extract_links(raw_response: str) -> list[dict] | None:
        """从 LLM 原始输出中提取 <links> 标记中的学习链接数组"""
        import re

        match = re.search(r'<links>([\s\S]*?)</links>', raw_response, re.DOTALL)
        if not match:
            return None

        links_text = match.group(1).strip()
        # 移除可能的代码块包裹
        if links_text.startswith("```"):
            links_text = re.sub(r"^```\w*\s*", "", links_text)
            links_text = re.sub(r"\s*```$", "", links_text)

        try:
            links = json.loads(links_text)
            if isinstance(links, list) and len(links) > 0:
                # 校验并规范化链接字段
                normalized = []
                for link in links:
                    if not isinstance(link, dict):
                        continue
                    if not link.get("title") or not link.get("url"):
                        continue
                    normalized.append({
                        "id": link.get("id") or f"link_{len(normalized)}",
                        "type": link.get("type", "internal"),
                        "title": link["title"],
                        "url": link["url"],
                        "description": link.get("description", ""),
                        "icon": link.get("icon", "📚" if link.get("type") == "internal" else "🔗"),
                        "style": link.get("style", "card"),
                        "metadata": link.get("metadata", {}),
                    })
                return normalized if normalized else None
        except json.JSONDecodeError:
            pass
        return None


# 单例
_pipeline: TeacherPipeline | None = None


def get_pipeline() -> TeacherPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = TeacherPipeline()
    return _pipeline
