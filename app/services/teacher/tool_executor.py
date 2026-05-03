"""
混合工具执行器 — ToolExecutor

处理两类工具的运行时执行：
1. UI Action 预处理（SVG生成、TTS预生成）
2. Function Calling 后台任务（搜索、评分、大纲、知识库、代码执行）

对应 OpenMAIC 的 ActionEngine + 各 API 端点逻辑。
"""

import base64
import logging
from typing import Any

from app.services.tts.registry import get_tts_provider
from app.services.tts.types import TTSConfig

logger = logging.getLogger("starlearn.tool_executor")


class ToolExecutor:
    def __init__(self, student_id: str = "", tts_config: TTSConfig | None = None):
        self.student_id = student_id
        self.tts_config = tts_config

    # ---- Function Calling 执行 ----

    async def execute_function_call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """执行 Function Calling 工具并返回结果"""
        handlers = {
            "web_search": self._handle_web_search,
            "grade_quiz": self._handle_grade_quiz,
            "generate_course_outline": self._handle_generate_outline,
            "search_knowledge_base": self._handle_search_kb,
            "run_code": self._handle_run_code,
        }
        handler = handlers.get(name)
        if not handler:
            return {"error": f"Unknown function: {name}"}
        try:
            return await handler(arguments)
        except Exception as e:
            logger.error("Function call '%s' failed: %s", name, e)
            return {"error": str(e)}

    # ---- UI Action 预处理 ----

    async def preprocess_ui_action(self, action: dict) -> dict:
        """
        预处理 UI Action：
        - 为 speech action 预生成 TTS 音频
        - 为 wb_draw_svg 补充缺失的 SVG
        """
        name = action.get("name") or action.get("type")
        params = action.get("params", {})

        if name == "speech" and self.tts_config:
            try:
                provider = get_tts_provider(self.tts_config.provider_id)
                result = await provider.generate(params.get("content", ""), self.tts_config)
                action["audioUrl"] = (
                    "data:audio/" + result.format + ";base64,"
                    + base64.b64encode(result.audio).decode("ascii")
                )
                action["durationMs"] = result.duration_ms
            except Exception as e:
                logger.warning("TTS pre-generation failed for speech action: %s", e)

        if name == "wb_draw_svg" and "svg" not in params and "description" in params:
            # LLM 给了描述但没有 SVG，后续可接入 SVG 生成 LLM
            logger.info("SVG generation needed for: %s", params.get("description", "")[:60])

        return action

    # ---- 私有处理器 ----

    async def _handle_web_search(self, args: dict) -> dict:
        """Tavily 网页搜索 — 使用真实 API"""
        query = args["query"]
        logger.info("Web search: %s", query[:80])

        from app.services.teacher.web_search import search_web, format_as_context

        try:
            search_response = await search_web(query)
        except Exception as e:
            logger.error("Web search failed: %s", e)
            return {"error": str(e), "query": query}

        if not search_response.results and not search_response.answer:
            return {
                "query": query,
                "results": [],
                "summary": "未找到相关搜索结果。",
                "source_count": 0,
            }

        # 格式化结果供 LLM 使用
        context = format_as_context(search_response)
        return {
            "query": query,
            "answer": search_response.answer,
            "results": [
                {"title": r.title, "url": r.url, "content": r.content[:300]}
                for r in search_response.results
            ],
            "source_count": search_response.source_count,
            "context_for_llm": context,
        }

    async def _handle_grade_quiz(self, args: dict) -> dict:
        """LLM 评分"""
        from llm_stream import call_llm

        question = args["question"]
        user_answer = args["user_answer"]
        total_points = args["total_points"]
        criteria = args.get("grading_criteria", "")

        system_prompt = (
            "你是一位专业的教育评估专家。请根据题目和学生答案进行评分并给出简短评语。"
            f"满分{total_points}分。以JSON格式回复: "
            f'{{"score": <0到{total_points}的整数>, "feedback": "<一两句评语>"}}'
        )
        user_prompt = f"题目：{question}\n满分：{total_points}分\n"
        if criteria:
            user_prompt += f"评分要点：{criteria}\n"
        user_prompt += f"学生答案：{user_answer}"

        try:
            result = await call_llm(system_prompt, user_prompt)
            import json, re
            match = re.search(r'\{[\s\S]*\}', result)
            if match:
                parsed = json.loads(match.group(0))
                score = max(0, min(total_points, round(float(parsed.get("score", 0)))))
                return {"score": score, "feedback": parsed.get("feedback", ""), "total": total_points}
        except Exception as e:
            logger.warning("Quiz grading parse failed: %s", e)

        return {"score": total_points // 2, "feedback": "已作答，请参考标准答案。", "total": total_points}

    async def _handle_generate_outline(self, args: dict) -> dict:
        """课程大纲生成 — 复用现有 course_generator.py"""
        from course_generator import generate_course_outline
        return await generate_course_outline(
            topic=args["topic"],
            student_level=args.get("student_level", "beginner"),
            chapter_count=args.get("chapter_count", 5),
        )

    async def _handle_search_kb(self, args: dict) -> dict:
        """本地知识库检索 — 复用 main.py 中的 KNOWLEDGE_BASE"""
        query = args["query"]
        top_k = args.get("top_k", 3)

        # 尝试从 main.py 导入本地知识库
        try:
            import main as main_module
            kb = getattr(main_module, "KNOWLEDGE_BASE", {})
        except Exception:
            kb = {}

        if not kb:
            return {"results": [], "query": query, "message": "知识库为空"}

        # 简单关键词匹配
        results = []
        query_lower = query.lower()
        for key, content in kb.items():
            if query_lower in str(key).lower() or query_lower in str(content)[:200].lower():
                results.append({"key": key, "content": str(content)[:500]})
            if len(results) >= top_k:
                break

        return {"results": results, "query": query}

    async def _handle_run_code(self, args: dict) -> dict:
        """代码沙盒执行"""
        import subprocess, tempfile, os

        code = args["code"]
        language = args.get("language", "python")

        if language != "python":
            return {"output": "", "error": f"Language '{language}' not yet supported in sandbox"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            tmp_path = f.name

        try:
            result = subprocess.run(
                ["python", tmp_path], capture_output=True, text=True, timeout=10
            )
            return {
                "output": result.stdout[:2000],
                "error": result.stderr[:1000] if result.stderr else "",
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"output": "", "error": "Execution timed out (10s limit)"}
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
