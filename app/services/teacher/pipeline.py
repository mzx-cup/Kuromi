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
from typing import AsyncIterator

from app.services.teacher.tool_executor import ToolExecutor
from app.services.teacher.personas import get_persona_manager
from app.services.teacher.function_tools import BACKEND_TOOLS
from app.services.teacher.web_search import format_as_speech_context

logger = logging.getLogger("starlearn.pipeline")


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

        # 2. 构建消息（带 Function Calling tools）
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"学生说：{user_input}\n\n"
                "请按照你的教学风格，用碎片化交织的方式回复。"
                "边说边画，边说边指。如果有超出你知识范围的内容，"
                "使用 web_search 工具搜索最新信息。"
            )},
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
                messages.append({"role": "assistant", "content": full_response[:200] + "..."})
                messages.append({"role": "user", "content": (
                    f"以下是从网络/知识库搜索到的补充信息，请基于这些信息继续回复学生：\n\n{context_text}\n\n"
                    "请用你的教学风格整合这些信息，以碎片化交织的方式输出。"
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

        # 7. 完成
        yield {"event": "done", "data": {
            "agent": "teacher",
            "persona": persona,
            "full_text": full_response,
            "action_count": len(actions) if actions else 0,
            "function_calls": len(function_calls),
        }}

    # ---- LLM 流式调用 ----

    async def _stream_llm_with_tools(
        self, messages: list[dict], tools: list[dict] | None
    ) -> AsyncIterator[dict]:
        """
        调用 LLM 流式生成（带 Function Calling tools）。

        当前策略：由于讯飞/MiniMax streaming API 的 function calling 支持有限，
        先用非流式调用检测 function_call，再流式输出文本。
        """
        try:
            from llm_stream import call_llm_async

            full_text = await call_llm_async(
                messages[0]["content"],
                messages[-1]["content"],
                temperature=0.7,
            )

            # 检查是否包含 function_call（简单模式匹配）
            fc_data = self._detect_function_call(full_text)
            if fc_data:
                yield {
                    "type": "function_call",
                    "id": fc_data.get("id", "fc_1"),
                    "name": fc_data["name"],
                    "arguments": fc_data.get("arguments", {}),
                }
            else:
                # 流式输出文本
                for i, char in enumerate(full_text):
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

        # 移除可能的 function_call 标签
        text = re.sub(r'<function_call>.*?</function_call>', '', text, flags=re.DOTALL)

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


# 单例
_pipeline: TeacherPipeline | None = None


def get_pipeline() -> TeacherPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = TeacherPipeline()
    return _pipeline
